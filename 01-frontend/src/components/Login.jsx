import { useState } from 'react'

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('alfa-hack-2026')
  const [password, setPassword] = useState('password123')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await onLogin(email, password)
    } catch (err) {
      setError(err?.message || 'Не удалось войти. Попробуйте ещё раз.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-3 justify-center mb-6">
          <div className="w-10 h-10 bg-red-600 rounded-full flex items-center justify-center font-bold text-white text-xl">
            А
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white leading-tight">Альфа-Инсайт</h1>
            <p className="text-slate-400 text-sm">Новостная аналитика для бизнеса</p>
          </div>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-slate-800 border border-slate-700 rounded-2xl p-6 shadow-xl"
        >
          <h2 className="text-lg font-semibold text-white mb-4">Вход в «Альфа-Бизнес»</h2>

          <label className="block text-sm text-slate-300 mb-1">Логин (email)</label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-white mb-4 outline-none focus:border-red-500"
            placeholder="alfa-hack-2026"
            autoComplete="username"
          />

          <label className="block text-sm text-slate-300 mb-1">Пароль</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-white mb-4 outline-none focus:border-red-500"
            placeholder="••••••••"
            autoComplete="current-password"
          />

          {error && (
            <div className="text-red-400 text-sm mb-4 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white py-2.5 rounded-lg font-medium transition-colors cursor-pointer"
          >
            {loading ? 'Входим…' : 'Войти'}
          </button>

          <p className="text-slate-500 text-xs mt-4 text-center">
            Тестовый аккаунт жюри: <span className="text-slate-300">alfa-hack-2026</span> /{' '}
            <span className="text-slate-300">password123</span>
          </p>
        </form>
      </div>
    </div>
  )
}
