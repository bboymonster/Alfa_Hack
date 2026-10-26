import { useRef, useState } from "react";
import Icon from "./Icon";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("alfa-hack-2026");
  const [password, setPassword] = useState("password123");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const errorRef = useRef(null);

  async function handleSubmit(event) {
    event.preventDefault();
    if (loading) return;
    const login = email.trim();
    if (!login || !password) {
      setError("Введите логин и пароль.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await onLogin(login, password);
    } catch (err) {
      setError(err?.message || "Не удалось войти. Проверьте логин и пароль.");
      // Сообщение озвучит скринридер, а фокус вернётся к полю для исправления.
      window.setTimeout(() => errorRef.current?.focus(), 0);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-intro">
        <div className="brand">
          <span className="brand-mark">
            А<span />
          </span>
          <span>
            Альфа / <strong>Инсайт</strong>
          </span>
        </div>
        <div className="login-story">
          <span className="eyebrow">ДЛЯ ТЕХ, КТО ПРИНИМАЕТ РЕШЕНИЯ</span>
          <h1>
            Меньше новостей.
            <br />
            <span>Больше смысла.</span>
          </h1>
          <p>
            Главное для вашей компании: что произошло, как это повлияет на бизнес и
            что можно сделать.
          </p>
          <div className="login-preview">
            <span className="badge">
              <Icon name="spark" size={14} /> Персональный инсайт
            </span>
            <h2>Контекст превращает новость в решение</h2>
            <p>Отрасль, профиль компании и ваша роль — в основе каждого разбора.</p>
            <div className="preview-flow">
              <span>Новость</span>
              <Icon name="arrow" size={16} />
              <span>Ваш бизнес</span>
              <Icon name="arrow" size={16} />
              <strong>Следующий шаг</strong>
            </div>
          </div>
        </div>
        <span className="login-footnote">Проект команды · Альфа-Будущее Хакатон 2026</span>
      </section>
      <section className="login-form-side">
        <div className="login-form-card">
          <span className="eyebrow">ДОБРО ПОЖАЛОВАТЬ</span>
          <h2>Войти в Инсайт</h2>
          <p className="muted">Ваша повестка начинается здесь.</p>
          <form onSubmit={handleSubmit} noValidate aria-busy={loading}>
            <label htmlFor="login-email">Логин</label>
            <input
              id="login-email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              disabled={loading}
              aria-invalid={!!error}
              required
            />
            <label htmlFor="login-password">Пароль</label>
            <div className="password-field">
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                disabled={loading}
                aria-invalid={!!error}
                required
              />
              <button
                type="button"
                className="icon-button"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? "Скрыть пароль" : "Показать пароль"}
                aria-pressed={showPassword}
                disabled={loading}
              >
                <Icon name={showPassword ? "eyeOff" : "eye"} />
              </button>
            </div>
            {error && (
              <p className="error-message" role="alert" tabIndex={-1} ref={errorRef}>
                {error}
              </p>
            )}
            <button
              type="submit"
              className="button button-primary login-submit"
              disabled={loading}
              aria-busy={loading}
            >
              {loading ? "Входим…" : "Продолжить"}
              {loading ? (
                <span className="spinner spinner-on-primary" aria-hidden="true" />
              ) : (
                <Icon name="arrow" size={18} />
              )}
            </button>
          </form>
          <div className="demo-account">
            <strong>Тестовый аккаунт жюри</strong>
            <span>alfa-hack-2026 / password123</span>
            <span>Данные уже заполнены — нажмите «Продолжить».</span>
          </div>
        </div>
      </section>
    </main>
  );
}
