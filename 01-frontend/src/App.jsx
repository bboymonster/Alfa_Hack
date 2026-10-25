import { useCallback, useEffect, useState } from 'react'
import * as api from './api'
import Header from './components/Header'
import Login from './components/Login'
import NewsCard from './components/NewsCard'

export default function App() {
  const [token, setTokenState] = useState(() => api.getToken())
  const [user, setUser] = useState(null)
  const [companies, setCompanies] = useState([])
  const [feed, setFeed] = useState([])
  const [companyId, setCompanyId] = useState('')
  const [role, setRole] = useState('CEO')
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [demo, setDemo] = useState(false)

  const loadFeed = useCallback(
    async (tok, currentCompanyId, currentRole, favOnly) => {
      setLoading(true)
      setError('')
      try {
        const items = await api.getFeed(tok, {
          company_id: currentCompanyId,
          role: currentRole,
          favorites_only: favOnly,
        })
        setFeed(items)
      } catch (err) {
        setError(err?.message || 'Не удалось загрузить ленту.')
        setFeed([])
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  async function handleLogin(email, password) {
    const data = await api.login(email, password)
    setTokenState(data.access_token)
    setUser(data.user)
    setCompanyId(data.user.current_company_id)
    setRole(data.user.role)
    setDemo(api.isDemo())
  }

  useEffect(() => {
    if (!token) return
    let cancelled = false
    ;(async () => {
      try {
        const list = await api.getCompanies(token)
        if (cancelled) return
        setCompanies(list)
        if (!companyId && list.length > 0) setCompanyId(list[0].synthetic_u)
        setDemo(api.isDemo())
      } catch {
        /* ignore */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token])

  useEffect(() => {
    if (!token || !companyId) return
    loadFeed(token, companyId, role, favoritesOnly)
  }, [token, companyId, role, favoritesOnly, loadFeed])

  async function handleToggleFavorite(feedItemId, isFavorite) {
    await api.setFavorite(token, feedItemId, isFavorite)
    setFeed((items) =>
      items.map((item) => (item.id === feedItemId ? { ...item, is_favorite: isFavorite } : item)),
    )
  }

  function handleLogout() {
    api.logout()
    setTokenState(null)
    setUser(null)
    setCompanies([])
    setFeed([])
    setFavoritesOnly(false)
  }

  if (!token || !user) {
    return <Login onLogin={handleLogin} />
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <Header
        user={user}
        companies={companies}
        companyId={companyId}
        role={role}
        demo={demo}
        favoritesOnly={favoritesOnly}
        onChangeCompany={(id) => setCompanyId(id)}
        onChangeRole={(r) => setRole(r)}
        onToggleFavorites={() => setFavoritesOnly((v) => !v)}
        onLogout={handleLogout}
      />

      <main className="max-w-5xl mx-auto px-4 pb-12">
        <div className="flex items-center justify-between mt-6 mb-4">
          <h1 className="text-2xl font-bold text-white">
            {favoritesOnly ? 'Избранное' : 'Лента «Новость-Инсайт»'}
          </h1>
          <span className="text-slate-500 text-sm">{feed.length} карточек</span>
        </div>

        {error && (
          <div className="text-red-400 text-sm mb-4 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-slate-400 text-center py-16">Загружаем ленту…</div>
        ) : feed.length === 0 ? (
          <div className="text-slate-400 text-center py-16">
            Нет карточек для выбранной компании и роли.
          </div>
        ) : (
          feed.map((item) => (
            <NewsCard
              key={item.id}
              item={item}
              onAsk={(id, question) => api.ask(token, id, question)}
              onToggleFavorite={handleToggleFavorite}
            />
          ))
        )}
      </main>
    </div>
  )
}
