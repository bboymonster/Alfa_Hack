import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "./api";
import Header from "./components/Header";
import Login from "./components/Login";
import NewsCard from "./components/NewsCard";
import Icon from "./components/Icon";
import Toast from "./components/Toast";
import { FeedSkeleton, TextSkeleton } from "./components/Skeleton";

const ALL_TOPICS = "Все темы";
const HIGH_PRIORITY_SCORE = 8;

export default function App() {
  const [token, setTokenState] = useState(() => api.getToken());
  const [user, setUser] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [feed, setFeed] = useState([]);
  const [companyId, setCompanyId] = useState("");
  const [role, setRole] = useState("CEO");
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [demo, setDemo] = useState(false);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState(ALL_TOPICS);
  const [revision, setRevision] = useState(0);
  const [notice, setNotice] = useState(null);
  const contextKey = useRef("");

  const closeNotice = useCallback(() => setNotice(null), []);

  const resetSession = useCallback((message) => {
    api.logout();
    setTokenState(null);
    setUser(null);
    setCompanies([]);
    setFeed([]);
    setCompanyId("");
    setFavoritesOnly(false);
    setSearch("");
    setCategory(ALL_TOPICS);
    setError("");
    setNotice(message ? { text: message, tone: "info" } : null);
  }, []);

  // Единая реакция на 401 из любого запроса: сессия истекла — возвращаемся к входу.
  useEffect(() => {
    api.onUnauthorized((err) => resetSession(err.message));
    return () => api.onUnauthorized(null);
  }, [resetSession]);

  async function handleLogin(email, password) {
    const data = await api.login(email, password);
    setNotice(null);
    setTokenState(data.access_token);
  }

  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    Promise.all([api.getMe(token), api.getCompanies(token)])
      .then(([profile, list]) => {
        if (cancelled) return;
        setUser(profile);
        setCompanyId(profile.current_company_id || list[0]?.synthetic_u || "");
        setRole(profile.role || "CEO");
        setCompanies(list);
        setDemo(api.isDemo());
      })
      .catch((err) => {
        if (cancelled) return;
        // 401 уже обработан глобально; остальное — показать и вернуть к входу.
        if (err?.code !== "unauthorized")
          resetSession(err?.message || "Не удалось загрузить профиль.");
      });
    return () => {
      cancelled = true;
    };
  }, [token, resetSession]);

  useEffect(() => {
    if (!token || !companyId) return undefined;
    let cancelled = false;
    const nextKey = `${companyId}|${role}|${favoritesOnly}`;
    // Смена контекста — показываем скелетоны; ручное обновление — не прячем ленту.
    const contextChanged = contextKey.current !== nextKey;
    contextKey.current = nextKey;
    Promise.resolve().then(async () => {
      if (cancelled) return;
      setLoading(true);
      setError("");
      if (contextChanged) setFeed([]);
      try {
        const items = await api.getFeed(token, {
          company_id: companyId,
          role,
          favorites_only: favoritesOnly,
        });
        if (!cancelled) setFeed(items);
      } catch (err) {
        if (!cancelled) {
          setError(err?.message || "Не удалось загрузить ленту.");
          if (contextChanged) setFeed([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [token, companyId, role, favoritesOnly, revision]);

  const refresh = useCallback(() => setRevision((value) => value + 1), []);

  async function handleToggleFavorite(feedItemId, isFavorite) {
    // Оптимистично обновляем, при ошибке откатываем и сообщаем.
    const apply = (value) =>
      setFeed((items) =>
        items.map((item) =>
          item.id === feedItemId ? { ...item, is_favorite: value } : item,
        ),
      );
    apply(isFavorite);
    try {
      await api.setFavorite(token, feedItemId, isFavorite);
      if (favoritesOnly && !isFavorite)
        setFeed((items) => items.filter((item) => item.id !== feedItemId));
    } catch (err) {
      apply(!isFavorite);
      throw err;
    }
  }

  function handleChangeCompany(nextId) {
    setCompanyId(nextId);
    setSearch("");
    setCategory(ALL_TOPICS);
  }

  if (!token)
    return (
      <>
        <Login onLogin={handleLogin} />
        <Toast notice={notice} onClose={closeNotice} />
      </>
    );
  if (!user)
    return (
      <main className="page-state" role="status" aria-live="polite">
        <span className="spinner spinner-large" aria-hidden="true" />
        <span>Загружаем ваш профиль…</span>
      </main>
    );

  const categories = [
    ALL_TOPICS,
    ...new Set(feed.map((item) => item.news?.category).filter(Boolean)),
  ];
  const activeCategory = categories.includes(category) ? category : ALL_TOPICS;
  const query = search.trim().toLocaleLowerCase("ru");
  const visibleFeed = feed.filter((item) => {
    if (activeCategory !== ALL_TOPICS && item.news?.category !== activeCategory)
      return false;
    if (!query) return true;
    const text =
      `${item.news?.title ?? ""} ${item.news?.summary_facts ?? ""} ${item.insight?.why_it_matters ?? ""}`.toLocaleLowerCase(
        "ru",
      );
    return text.includes(query);
  });
  const highPriority = feed.filter(
    (item) => item.importance_score >= HIGH_PRIORITY_SCORE,
  ).length;
  const company = companies.find((item) => item.synthetic_u === companyId);
  const hasFilters = query !== "" || activeCategory !== ALL_TOPICS;
  const showSkeleton = loading && feed.length === 0;
  const showError = !loading && !!error;

  function clearFilters() {
    setSearch("");
    setCategory(ALL_TOPICS);
  }

  function renderFeedBody() {
    if (showSkeleton) return <FeedSkeleton />;
    if (showError && feed.length === 0)
      return (
        <div className="empty-state error-state" role="alert">
          <span className="empty-icon empty-icon-error">
            <Icon name="alert" size={26} />
          </span>
          <h2>Не удалось загрузить ленту</h2>
          <p>{error}</p>
          <button type="button" className="button button-primary" onClick={refresh}>
            <Icon name="refresh" size={16} />
            Повторить
          </button>
        </div>
      );
    if (visibleFeed.length)
      return (
        <div className={`feed-list ${loading ? "is-refreshing" : ""}`} aria-busy={loading}>
          {visibleFeed.map((item) => (
            <NewsCard
              key={item.id}
              item={item}
              onAsk={(id, question) => api.ask(token, id, question)}
              onToggleFavorite={handleToggleFavorite}
            />
          ))}
        </div>
      );
    if (favoritesOnly && !hasFilters)
      return (
        <div className="empty-state">
          <span className="empty-icon">
            <Icon name="bookmark" size={26} />
          </span>
          <h2>В избранном пока пусто</h2>
          <p>Сохраняйте карточки значком закладки, чтобы вернуться к ним позже.</p>
          <button
            type="button"
            className="button button-subtle"
            onClick={() => setFavoritesOnly(false)}
          >
            Перейти ко всей ленте
          </button>
        </div>
      );
    if (hasFilters)
      return (
        <div className="empty-state">
          <span className="empty-icon">
            <Icon name="search" size={26} />
          </span>
          <h2>Ничего не найдено</h2>
          <p>Попробуйте другую тему или измените поисковый запрос.</p>
          <button type="button" className="button button-subtle" onClick={clearFilters}>
            Сбросить фильтры
          </button>
        </div>
      );
    return (
      <div className="empty-state">
        <span className="empty-icon">
          <Icon name="grid" size={26} />
        </span>
        <h2>Повестка пока пуста</h2>
        <p>Для этой компании и роли новых карточек ещё нет. Загляните позже.</p>
        <button type="button" className="button button-subtle" onClick={refresh}>
          <Icon name="refresh" size={16} />
          Обновить
        </button>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Перейти к содержимому
      </a>
      <Header
        user={user}
        companies={companies}
        companyId={companyId}
        role={role}
        demo={demo}
        onChangeCompany={handleChangeCompany}
        onChangeRole={setRole}
        onLogout={() => resetSession()}
      />
      <main className="main-content" id="main">
        <section className="feed-intro">
          <div>
            <span className="eyebrow">ВАШ БИЗНЕС В КОНТЕКСТЕ СОБЫТИЙ</span>
            <h1>
              Повестка, которая <span>касается вас.</span>
            </h1>
            <p>Важные новости. Короткие выводы. Понятные действия.</p>
          </div>
          <div className="intro-sign" aria-hidden="true">
            <Icon name="spark" size={44} />
            <span>
              От события
              <br />
              <strong>к решению</strong>
            </span>
          </div>
        </section>
        <section className="overview-grid" aria-label="Обзор ленты">
          <div className="overview-card">
            <span className="overview-icon">
              <Icon name="grid" />
            </span>
            <div>
              <strong>{showSkeleton ? <TextSkeleton width={36} /> : feed.length}</strong>
              <span>{favoritesOnly ? "в избранном" : "в вашей повестке"}</span>
            </div>
          </div>
          <div className="overview-card">
            <span className="overview-icon overview-icon-red">
              <Icon name="spark" />
            </span>
            <div>
              <strong>{showSkeleton ? <TextSkeleton width={36} /> : highPriority}</strong>
              <span>высокой важности</span>
            </div>
          </div>
          <div className="overview-card overview-company">
            <span className="overview-icon">
              <Icon name="building" />
            </span>
            <div>
              <strong title={company?.name}>{company?.city || "Компания"}</strong>
              <span title={company?.mainokved_name}>
                {company?.mainokved_name || "Персональный контекст"}
              </span>
            </div>
          </div>
        </section>
        <section className="feed-workspace" aria-label="Лента новостей и инсайтов">
          <div className="feed-toolbar">
            <div className="feed-tabs" role="group" aria-label="Раздел ленты">
              <button
                type="button"
                className={!favoritesOnly ? "active" : ""}
                aria-pressed={!favoritesOnly}
                onClick={() => setFavoritesOnly(false)}
              >
                Вся лента
              </button>
              <button
                type="button"
                className={favoritesOnly ? "active" : ""}
                aria-pressed={favoritesOnly}
                onClick={() => setFavoritesOnly(true)}
              >
                <Icon name="bookmark" size={16} />
                Избранное
              </button>
            </div>
            <label className="search-field">
              <Icon name="search" size={18} />
              <input
                type="search"
                aria-label="Поиск по ленте"
                placeholder="Найти в повестке"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Escape") setSearch("");
                }}
              />
              {search && (
                <button
                  type="button"
                  className="icon-button search-clear"
                  onClick={() => setSearch("")}
                  aria-label="Очистить поиск"
                >
                  <Icon name="close" size={14} />
                </button>
              )}
            </label>
          </div>
          <div className="feed-filters">
            <label className="topic-select">
              <select
                aria-label="Тема новостей"
                value={activeCategory}
                onChange={(event) => setCategory(event.target.value)}
                disabled={showSkeleton}
              >
                {categories.map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
              <Icon name="chevron" size={15} />
            </label>
            <span>По важности</span>
            <button
              type="button"
              className="refresh-button"
              onClick={refresh}
              disabled={loading}
              aria-label="Обновить ленту"
            >
              <Icon name="refresh" size={14} className={loading ? "is-spinning" : ""} />
              {loading ? "Обновляем…" : "Обновить"}
            </button>
          </div>
          <div className="feed-status" role="status" aria-live="polite">
            {showSkeleton
              ? "Собираем главное для вас…"
              : showError
                ? "Лента не обновлена"
                : `${formatCards(visibleFeed.length)} · с учётом вашей компании и роли`}
          </div>
          {showError && feed.length > 0 && (
            <div className="inline-alert" role="alert">
              <Icon name="alert" size={16} />
              <span>{error}</span>
              <button type="button" className="inline-alert-action" onClick={refresh}>
                Повторить
              </button>
            </div>
          )}
          {renderFeedBody()}
        </section>
        <footer className="app-footer">
          <span>Альфа / Инсайт</span>
          <span>Проект команды · Хакатон 2026</span>
        </footer>
      </main>
      <Toast notice={notice} onClose={closeNotice} />
    </div>
  );
}

function formatCards(count) {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return `${count} карточка`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14))
    return `${count} карточки`;
  return `${count} карточек`;
}
