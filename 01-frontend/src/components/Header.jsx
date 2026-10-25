const ROLES = [
  { value: 'CEO', label: 'CEO · Собственник' },
  { value: 'CFO', label: 'CFO · Казначей' },
  { value: 'ACCOUNTANT', label: 'Бухгалтер · Главный бухгалтер' },
]

export default function Header({
  user,
  companies,
  companyId,
  role,
  demo,
  favoritesOnly,
  onChangeCompany,
  onChangeRole,
  onToggleFavorites,
  onLogout,
}) {
  const selectedCompany = companies.find((c) => c.synthetic_u === companyId)

  return (
    <header className="sticky top-0 z-20 border-b border-[--color-border] bg-[--color-surface-card]/70 backdrop-blur-xl supports-[backdrop-filter]:bg-[--color-surface-card]/60">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
        {/* Бренд */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[--color-alfa-red] to-[--color-alfa-gold] flex items-center justify-center font-bold text-white text-lg shadow-lg shadow-[--color-alfa-red]/25">
            А
          </div>
          <div>
            <span className="text-xl font-extrabold text-white">Альфа‑Инсайт</span>
            {demo && (
              <span className="ml-2 text-[10px] font-semibold bg-amber-400/15 text-amber-300 px-2 py-0.5 rounded align-middle border border-amber-500/30">
                демо‑режим
              </span>
            )}
          </div>
        </div>

        {/* Контролы */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Выбор компании */}
          <div className="relative">
            <select
              value={companyId}
              onChange={(e) => onChangeCompany(e.target.value)}
              className="appearance-none bg-[--color-surface-elev] border border-[--color-border] rounded-lg pl-3 pr-9 py-2 text-sm text-white focus:border-[--color-alfa-red] transition-colors hover:border-[--color-border-hover]"
            >
              {companies.map((company) => (
                <option key={company.synthetic_u} value={company.synthetic_u}>
                  {company.name} ({company.synthetic_u})
                </option>
              ))}
            </select>
            <svg
              className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[--color-text-dim] pointer-events-none"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M6 9l6 6 6-6" />
            </svg>
          </div>

          {/* Выбор роли */}
          <div className="relative">
            <select
              value={role}
              onChange={(e) => onChangeRole(e.target.value)}
              className="appearance-none bg-[--color-surface-elev] border border-[--color-border] rounded-lg pl-3 pr-9 py-2 text-sm text-white focus:border-[--color-alfa-red] transition-colors hover:border-[--color-border-hover]"
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
            <svg
              className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[--color-text-dim] pointer-events-none"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M6 9l6 6 6-6" />
            </svg>
          </div>

          {/* Избранное */}
          <button
            onClick={onToggleFavorites}
            className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-200 border ${
              favoritesOnly
                ? 'bg-amber-400/15 border-amber-500/50 text-amber-300'
                : 'bg-[--color-surface-elev] border-[--color-border] text-[--color-text-dim] hover:bg-[--color-border-hover] hover:text-[--color-text]'
            }`}
          >
            ★ Избранное
          </button>

          {/* Пользователь */}
          <div className="flex items-center gap-2 pl-1 border-l border-[--color-border]">
            <span className="text-[--color-text-dim] text-sm hidden lg:inline">{user.full_name}</span>
            <button
              onClick={onLogout}
              className="text-sm text-[--color-text-dim] hover:text-[--color-text] px-2 py-1 rounded transition-colors"
            >
              Выйти
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
