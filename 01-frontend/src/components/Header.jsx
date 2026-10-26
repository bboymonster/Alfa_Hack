import Icon from "./Icon";

const ROLES = [
  { value: "CEO", label: "Собственник · CEO" },
  { value: "CFO", label: "Финансовый директор · CFO" },
  { value: "ACCOUNTANT", label: "Главный бухгалтер" },
];

export default function Header({
  user,
  companies,
  companyId,
  role,
  demo,
  onChangeCompany,
  onChangeRole,
  onLogout,
}) {
  const fullName = user?.full_name || user?.email || "Пользователь";
  return (
    <header className="app-header">
      <div className="header-main">
        <a href="#main" className="brand" aria-label="Альфа-Инсайт — перейти к ленте">
          <span className="brand-mark">
            А<span />
          </span>
          <span>
            Альфа<span className="brand-divider"> / </span>
            <strong>Инсайт</strong>
          </span>
        </a>
        <span className="header-product">Аналитика для бизнеса</span>
        <div className="header-user">
          {demo && (
            <span
              className="badge badge-demo"
              title="Сервер недоступен: данные демонстрационные и хранятся только в браузере"
            >
              Демо
            </span>
          )}
          <span className="user-name" title={fullName}>
            {fullName}
          </span>
          <span className="avatar" aria-hidden="true">
            {fullName.trim().slice(0, 1).toUpperCase() || "А"}
          </span>
          <button
            type="button"
            className="icon-button"
            onClick={onLogout}
            aria-label="Выйти"
            title="Выйти"
          >
            <Icon name="exit" />
          </button>
        </div>
      </div>
      <div className="context-bar">
        <label className="context-select company-select">
          <Icon name="building" />
          <select
            aria-label="Компания"
            value={companyId}
            onChange={(event) => onChangeCompany(event.target.value)}
            disabled={companies.length === 0}
          >
            {companies.length === 0 && <option value="">Компании не найдены</option>}
            {companies.map((company) => (
              <option key={company.synthetic_u} value={company.synthetic_u}>
                {company.name}
              </option>
            ))}
          </select>
          <Icon name="chevron" size={16} />
        </label>
        <label className="context-select role-select">
          <span className="field-hint">Ваша роль</span>
          <select
            aria-label="Ваша роль"
            value={role}
            onChange={(event) => onChangeRole(event.target.value)}
          >
            {ROLES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <Icon name="chevron" size={16} />
        </label>
      </div>
    </header>
  );
}
