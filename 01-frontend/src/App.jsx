import { useEffect, useState } from "react";
import * as api from "./api";
import Header from "./components/Header";
import Login from "./components/Login";
import NewsCard from "./components/NewsCard";
import Icon from "./components/Icon";

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
  const [category, setCategory] = useState("Все темы");
  const [revision, setRevision] = useState(0);

  async function handleLogin(email, password) {
    const data = await api.login(email, password);
    setTokenState(data.access_token);
  }

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    Promise.all([api.getMe(token), api.getCompanies(token)])
      .then(([profile, list]) => {
        if (cancelled) return;
        setUser(profile);
        setCompanyId(profile.current_company_id);
        setRole(profile.role);
        setCompanies(list);
        setDemo(api.isDemo());
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.message || "Не удалось загрузить профиль.");
        api.logout();
        setTokenState(null);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!token || !companyId) return;
    let cancelled = false;
    // Запуск асинхронной загрузки также отменяется при быстрой смене компании/роли.
    Promise.resolve().then(async () => {
      if (cancelled) return;
      setLoading(true);
      setError("");
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
          setFeed([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [token, companyId, role, favoritesOnly, revision]);

  async function handleToggleFavorite(feedItemId, isFavorite) {
    await api.setFavorite(token, feedItemId, isFavorite);
    setFeed((items) =>
      items
        .map((item) =>
          item.id === feedItemId ? { ...item, is_favorite: isFavorite } : item,
        )
        .filter((item) => !favoritesOnly || item.is_favorite),
    );
  }

  function handleLogout() {
    api.logout();
    setTokenState(null);
    setUser(null);
    setCompanies([]);
    setFeed([]);
    setCompanyId("");
    setFavoritesOnly(false);
    setSearch("");
    setCategory("Все темы");
  }

  if (!token)
    return (
      <>
        <Login onLogin={handleLogin} />
        {error && (
          <div className="login-error error-message" role="alert">
            {error}
          </div>
        )}
      </>
    );
  if (!user)
    return (
      <main className="page-state" role="status">
        Загружаем ваш профиль…
      </main>
    );

  const categories = [
    "Все темы",
    ...new Set(feed.map((item) => item.news.category)),
  ];
  const activeCategory = categories.includes(category) ? category : "Все темы";
  const visibleFeed = feed.filter((item) => {
    const text =
      `${item.news.title} ${item.news.summary_facts} ${item.insight.why_it_matters}`.toLocaleLowerCase(
        "ru",
      );
    return (
      (activeCategory === "Все темы" ||
        item.news.category === activeCategory) &&
      text.includes(search.trim().toLocaleLowerCase("ru"))
    );
  });
  const highPriority = feed.filter((item) => item.importance_score >= 8).length;
  const company = companies.find((item) => item.synthetic_u === companyId);

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
        onChangeCompany={setCompanyId}
        onChangeRole={setRole}
        onLogout={handleLogout}
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
              <strong>{loading ? "—" : feed.length}</strong>
              <span>{favoritesOnly ? "в избранном" : "в вашей повестке"}</span>
            </div>
          </div>
          <div className="overview-card">
            <span className="overview-icon overview-icon-red">
              <Icon name="spark" />
            </span>
            <div>
              <strong>{loading ? "—" : highPriority}</strong>
              <span>высокой важности</span>
            </div>
          </div>
          <div className="overview-card overview-company">
            <span className="overview-icon">
              <Icon name="building" />
            </span>
            <div>
              <strong>{company?.city || "Компания"}</strong>
              <span>{company?.mainokved_name || "Персональный контекст"}</span>
            </div>
          </div>
        </section>
        <section
          className="feed-workspace"
          aria-label="Лента новостей и инсайтов"
        >
          <div className="feed-toolbar">
            <div className="feed-tabs" role="group" aria-label="Раздел ленты">
              <button
                className={!favoritesOnly ? "active" : ""}
                aria-pressed={!favoritesOnly}
                onClick={() => setFavoritesOnly(false)}
              >
                Вся лента
              </button>
              <button
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
                aria-label="Поиск по ленте"
                placeholder="Найти в повестке"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
          </div>
          <div className="feed-filters">
            <label className="topic-select">
              <select
                aria-label="Тема новостей"
                value={activeCategory}
                onChange={(event) => setCategory(event.target.value)}
              >
                {categories.map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
              <Icon name="chevron" size={15} />
            </label>
            <span>По важности</span>
            <button
              className="refresh-button"
              onClick={() => setRevision((value) => value + 1)}
              disabled={loading}
            >
              Обновить
            </button>
          </div>
          <div className="feed-status" role="status">
            {loading
              ? "Обновляем вашу повестку…"
              : `${visibleFeed.length} карточек · с учётом вашей компании и роли`}
          </div>
          {error && (
            <p className="error-message" role="alert">
              {error}
            </p>
          )}
          {loading ? (
            <div className="feed-loading" role="status">
              <span className="loading-dot" />
              Собираем главное для вас…
            </div>
          ) : visibleFeed.length ? (
            <div className="feed-list">
              {visibleFeed.map((item) => (
                <NewsCard
                  key={item.id}
                  item={item}
                  onAsk={(id, question) => api.ask(token, id, question)}
                  onToggleFavorite={handleToggleFavorite}
                />
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <Icon name={favoritesOnly ? "bookmark" : "search"} size={30} />
              <h2>
                {favoritesOnly
                  ? "Всё важное — под рукой"
                  : "Пока ничего не найдено"}
              </h2>
              <p>
                {favoritesOnly
                  ? "Сохраняйте карточки значком закладки, чтобы вернуться к ним позже."
                  : "Попробуйте другую тему или измените поисковый запрос."}
              </p>
            </div>
          )}
        </section>
        <footer className="app-footer">
          <span>Альфа / Инсайт</span>
          <span>Проект команды · Хакатон 2026</span>
        </footer>
      </main>
    </div>
  );
}
