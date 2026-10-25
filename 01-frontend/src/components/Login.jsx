import { useState } from 'react'

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('alfa-hack-2026')
  const [password, setPassword] = useState('password123')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await onLogin(email, password)
    } catch (err) {
      setError(err?.message || 'Не удалось войти. Проверьте логин и пароль.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[--color-surface] via-[--color-surface-elev] to-[--color-surface] flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-8 animate-fadeIn">
        {/* Логотип */}
        <div className="flex items-center justify-center gap-3 text-center">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[--color-alfa-red] to-[--color-alfa-gold] flex items-center justify-center font-bold text-white text-2xl shadow-lg shadow-[--color-alfa-red]/30">
            А
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-white leading-tight">Альфа‑Инсайт</h1>
            <p className="text-[--color-text-dim] text-sm">Новостная аналитика для бизнеса</p>
          </div>
        </div>

        {/* Карточка входа */}
        <div className="relative rounded-2xl p-0.5 bg-gradient-to-br from-[--color-border] via-[--color-alfa-red]/20 to-[--color-border] shadow-2xl shadow-black/40">
          <div className="bg-[--color-surface-card] rounded-2xl p-8">
            <h2 className="text-xl font-semibold text-white mb-6">Вход в «Альфа‑Бизнес»</h2>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-[--color-text-dim] mb-1.5">Логин (email)</label>
                <input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[--color-surface-elev] border border-[--color-border] rounded-lg text-white text-sm transition-colors"
                  placeholder="alfa-hack-2026"
                  autoComplete="username"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[--color-text-dim] mb-1.5">Пароль</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-4 py-2.5 pr-11 bg-[--color-surface-elev] border border-[--color-border] rounded-lg text-white text-sm transition-colors"
                    placeholder="••••••••"
                    autoComplete="current-password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[--color-text-dim] hover:text-[--color-text] transition-colors"
                    aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                  >
                    {showPassword ? '○' : '●'}
                  </button>
                </div>
              </div>

              {error && (
                <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-[--color-alfa-red] to-[--color-alfa-red-hover] hover:brightness-110 disabled:opacity-60 text-white py-2.5 rounded-lg font-medium shadow-lg shadow-[--color-alfa-red]/25 transition-all duration-150"
              >
                {loading ? 'Входим…' : 'Войти'}
              </button>
            </form>

            <p className="mt-6 text-center text-xs text-[--color-text-dim]">
              Тестовый аккаунт жюри:{' '}
              <span className="text-[--color-text]">alfa-hack-2026</span> /{' '}
              <span className="text-[--color-text]">password123</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
