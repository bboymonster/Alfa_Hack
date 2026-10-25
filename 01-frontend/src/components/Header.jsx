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
  return (
    <header className="bg-slate-800 border-b border-slate-700 p-4 sticky top-0 z-10">
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center font-bold text-white">
            А
          </div>
          <div>
            <span className="text-xl font-bold text-white">Альфа-Инсайт</span>
            {demo && (
              <span className="ml-2 text-xs bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded align-middle">
                демо-режим
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <select
            value={companyId}
            onChange={(e) => onChangeCompany(e.target.value)}
            className="bg-slate-900 text-slate-200 border border-slate-600 rounded px-3 py-2 text-sm outline-none cursor-pointer"
          >
            {companies.map((company) => (
              <option key={company.synthetic_u} value={company.synthetic_u}>
                {company.name} ({company.synthetic_u})
              </option>
            ))}
          </select>

          <select
            value={role}
            onChange={(e) => onChangeRole(e.target.value)}
            className="bg-slate-900 text-slate-200 border border-slate-600 rounded px-3 py-2 text-sm outline-none cursor-pointer"
          >
            <option value="CEO">CEO / Собственник</option>
            <option value="CFO">CFO / Казначей</option>
            <option value="ACCOUNTANT">Главный бухгалтер</option>
          </select>

          <button
            onClick={onToggleFavorites}
            className={`px-3 py-2 rounded text-sm font-medium transition-colors cursor-pointer border ${
              favoritesOnly
                ? 'bg-amber-500/20 border-amber-500/50 text-amber-300'
                : 'bg-slate-900 border-slate-600 text-slate-300 hover:bg-slate-700'
            }`}
          >
            ★ Избранное
          </button>

          <div className="flex items-center gap-2 pl-1 border-l border-slate-700">
            <span className="text-slate-400 text-sm hidden lg:inline">{user.full_name}</span>
            <button
              onClick={onLogout}
              className="text-sm text-slate-400 hover:text-white px-2 py-1 rounded cursor-pointer transition-colors"
            >
              Выйти
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
