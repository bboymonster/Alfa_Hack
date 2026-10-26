"""Небольшое хранилище в памяти. Позже заменим его запросами к БД из 04-infra-db.

Инсайты по умолчанию строит ``mock_ai`` (мгновенно, без сети). Если передан
``AiClient``, фоном лента обогащается результатами 03-ai-service (агентная
трассировка, позиция банка из корпуса отчётов); при недоступности сервиса
каждый инсайт остаётся честной заглушкой.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Event, Lock, Thread
from uuid import NAMESPACE_URL, uuid5

from pwdlib import PasswordHash

from app.ai_client import AiClient
from app.mock_ai import generate_feed_insight
from app.schemas import Company, EnrichmentStatus, FeedItem, News, Role, User

password_hash = PasswordHash.recommended()


def stable_id(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"alfa-hack-demo/{name}"))


@dataclass
class StoredUser:
    profile: User
    hashed_password: str


class MemoryStore:
    def __init__(self, ai_client: AiClient | None = None) -> None:
        self.lock = Lock()
        self.ai_client = ai_client
        # ID и названия первых двух компаний совпадают с демо-профилями seed.py.
        # Значения ниже — самостоятельные фикстуры, исходные CSV не загружаются.
        companies = [
            Company(
                synthetic_u="U_1595",
                name='ООО "Модный Стиль Ритейл"',
                mainokved_code="47.71",
                mainokved_name="Розничная торговля одеждой",
                revenue_company=16_461_800_000,
                cl_product_loa_mark=True,
                fts_flag=True,
                city="Москва",
                region="Москва",
            ),
            Company(
                synthetic_u="U_1465",
                name='АО "Премиум Напитки Импорт"',
                mainokved_code="46.34",
                mainokved_name="Оптовая торговля напитками",
                revenue_company=44_401_190_000,
                cl_product_loa_mark=True,
                fts_flag=True,
                city="Москва",
                region="Москва",
            ),
            Company(
                synthetic_u="DEMO_LOCAL",
                name='ООО "Демо Локальный Сервис"',
                mainokved_code="62.01",
                mainokved_name="Разработка программного обеспечения",
                revenue_company=240_000_000,
                cl_product_loa_mark=False,
                fts_flag=False,
                city="Казань",
                region="Республика Татарстан",
            ),
        ]
        self.companies = {company.synthetic_u: company for company in companies}
        news_items = [
            News(
                id=stable_id("news/financing"),
                title="Демо: изменение стоимости заимствований",
                summary_facts="Учебный сценарий: стоимость новых кредитов изменилась.",
                source="Демонстрационные данные команды",
                published_at=datetime(2026, 9, 11, 13, 30, tzinfo=UTC),
                category="Финансы и макроэкономика",
            ),
            News(
                id=stable_id("news/logistics"),
                title="Демо: увеличение сроков международных поставок",
                summary_facts="Учебный сценарий: срок доставки по одному из маршрутов вырос.",
                source="Демонстрационные данные команды",
                published_at=datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
                category="Логистика",
            ),
            News(
                id=stable_id("news/reporting"),
                title="Демо: обновление требований к отчётности",
                summary_facts="Учебный сценарий: предложено изменение формы отчётности.",
                source="Демонстрационные данные команды",
                published_at=datetime(2026, 9, 9, 10, 0, tzinfo=UTC),
                category="Регулирование",
            ),
        ]
        self.feed: dict[str, FeedItem] = {}
        for company in companies:
            for role in Role:
                for index, news in enumerate(news_items):
                    # Для бухгалтера первой показываем отчётность, для CFO — финансирование.
                    score = 9 - index
                    if role == Role.ACCOUNTANT and news.category == "Регулирование":
                        score = 10
                    item = FeedItem(
                        id=stable_id(f"insight/{company.synthetic_u}/{role}/{news.id}"),
                        company_id=company.synthetic_u,
                        role=role,
                        news=news,
                        insight=generate_feed_insight(news, company, role),
                        importance_score=score,
                    )
                    self.feed[item.id] = item

        demo_hash = password_hash.hash("password123")
        self.dummy_password_hash = demo_hash
        self.users: dict[str, StoredUser] = {}
        for email, role in [
            ("alfa-hack-2026", Role.CEO),
            ("ceo@alfabusiness.ru", Role.CEO),
            ("cfo@alfabusiness.ru", Role.CFO),
            ("accountant@alfabusiness.ru", Role.ACCOUNTANT),
        ]:
            self.users[email] = StoredUser(
                profile=User(
                    id=stable_id(f"user/{email}"),
                    email=email,
                    full_name=f"Демо {role.value}",
                    role=role,
                    current_company_id="U_1595",
                    allowed_company_ids=list(self.companies),
                ),
                hashed_password=demo_hash,
            )
        # Как в текущей SQL-схеме: избранное привязано к пользователю и новости.
        self.favorites: set[tuple[str, str]] = set()

        self._stop = Event()
        self._worker: Thread | None = None
        self._enrichment = EnrichmentStatus(
            status="pending" if ai_client is not None and ai_client.enabled else "disabled",
            completed=0,
            total=len(self.feed),
        )

    def start_enrichment(self) -> None:
        """Запускается из lifespan, а не при импорте модуля или создании тестового app."""
        if self.ai_client is None or not self.ai_client.enabled or self._worker is not None:
            return
        self._worker = Thread(target=self._enrich_with_ai, name="ai-enrich", daemon=True)
        self._worker.start()

    def stop_enrichment(self) -> None:
        self._stop.set()
        if self._worker is not None:
            # Текущий urllib-запрос ограничен таймаутом; не задерживаем остановку API.
            self._worker.join(timeout=0.1)

    def enrichment_status(self) -> EnrichmentStatus:
        with self.lock:
            return self._enrichment.model_copy()

    def _enrich_with_ai(self) -> None:
        """Фоновое обогащение ленты инсайтами 03-ai-service (best-effort)."""
        assert self.ai_client is not None
        pending = list(self.feed.values())
        while pending and not self._stop.is_set():
            with self.lock:
                self._enrichment.status = "running"
            item = pending[0]
            result = self.ai_client.generate_insight(
                item.news, self.companies[item.company_id], item.role
            )
            if self._stop.is_set():
                break
            if result is None:
                if not self.ai_client.retryable:
                    # 422 и неверный формат ответа требуют исправления контракта, не ретрая.
                    with self.lock:
                        self._enrichment.status = "failed"
                    return
                # Один неуспешный вызов на интервал, а не 27 последовательных таймаутов.
                with self.lock:
                    self._enrichment.status = "retrying"
                self._stop.wait(self.ai_client.retry_interval_s)
                continue
            insight, score, is_demo = result
            with self.lock:
                self.feed[item.id] = item.model_copy(
                    update={
                        "insight": insight,
                        "importance_score": score,
                        # LLM не превращает вымышленную новость в реальный источник.
                        "is_demo": item.is_demo or is_demo,
                    }
                )
                self._enrichment.completed += 1
            pending.pop(0)
        with self.lock:
            self._enrichment.status = "stopped" if self._stop.is_set() else "complete"

    def user_by_id(self, user_id: str) -> StoredUser | None:
        return next((user for user in self.users.values() if user.profile.id == user_id), None)

    def with_favorite(self, item: FeedItem, user: User) -> FeedItem:
        return item.model_copy(update={"is_favorite": (user.id, item.news.id) in self.favorites})
