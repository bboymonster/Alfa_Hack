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
  return (
    <header className="app-header">
      <div className="header-main">
        <a
          href="#main"
          className="brand"
          aria-label="Альфа-Инсайт — перейти к ленте"
        >
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
          {demo && <span className="badge badge-demo">Демо</span>}
          <span className="user-name">{user.full_name}</span>
          <span className="avatar" aria-hidden="true">
            {user.full_name?.slice(0, 1) || "А"}
          </span>
          <button className="icon-button" onClick={onLogout} aria-label="Выйти">
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
          >
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
