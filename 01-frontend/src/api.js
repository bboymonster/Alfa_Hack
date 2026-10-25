// API-клиент к 02-backend с автоматическим переключением в автономный демо-режим,
// если backend недоступен (например, на статическом GitHub Pages).
import { DEMO_COMPANIES, buildDemoFeed, demoUser } from './demoData'

const TOKEN_KEY = 'alfa_news_token'

let demoMode = false
let demoFeed = null
let demoFavorites = new Set()

function isNetworkError(err) {
  return err instanceof TypeError || err?.name === 'TypeError'
}

async function request(path, { method = 'GET', token, body } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const data = await response.json()
      if (data?.detail) detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    } catch {
      /* ignore */
    }
    const error = new Error(detail)
    error.status = response.status
    throw error
  }
  return response.json()
}

export function isDemo() {
  return demoMode
}

export function getToken() {
  return typeof window !== 'undefined' ? window.localStorage.getItem(TOKEN_KEY) : null
}

function setToken(token) {
  if (typeof window !== 'undefined') {
    if (token) window.localStorage.setItem(TOKEN_KEY, token)
    else window.localStorage.removeItem(TOKEN_KEY)
  }
}

export async function login(email, password) {
  try {
    const data = await request('/api/auth/login', { method: 'POST', body: { email, password } })
    setToken(data.access_token)
    demoMode = false
    return data
  } catch (err) {
    if (isNetworkError(err) || err?.status >= 500) {
      // Backend недоступен — включаем автономную демонстрацию.
      demoMode = true
      demoFeed = buildDemoFeed()
      const user = demoUser(email || 'alfa-hack-2026')
      setToken('demo')
      return { access_token: 'demo', token_type: 'bearer', expires_in: 0, user }
    }
    throw err
  }
}

export async function getCompanies(token) {
  if (demoMode) return DEMO_COMPANIES
  return request('/api/companies', { token })
}

export async function getFeed(token, { company_id, role, favorites_only = false } = {}) {
  if (demoMode) {
    return demoFeed
      .filter(
        (item) =>
          item.company_id === (company_id || 'U_1595') &&
          item.role === (role || 'CEO') &&
          (!favorites_only || demoFavorites.has(item.news.id)),
      )
      .sort((a, b) => b.importance_score - a.importance_score)
      .map((item) => ({ ...item, is_favorite: demoFavorites.has(item.news.id) }))
  }
  const params = new URLSearchParams()
  if (company_id) params.set('company_id', company_id)
  if (role) params.set('role', role)
  if (favorites_only) params.set('favorites_only', 'true')
  const qs = params.toString()
  const data = await request(`/api/feed${qs ? `?${qs}` : ''}`, { token })
  return data.items
}

export async function ask(token, feedItemId, question) {
  if (demoMode) {
    const item = demoFeed.find((i) => i.id === feedItemId)
    return {
      feed_item_id: feedItemId,
      answer: `Демо-ответ по карточке «${item.news.title}». Ваш вопрос: «${question}». ` +
        `${item.insight.why_it_matters} Рекомендуемый шаг: ${item.insight.action_item}`,
      is_demo: true,
    }
  }
  return request(`/api/feed/${feedItemId}/ask`, { method: 'POST', token, body: { question } })
}

export async function setFavorite(token, feedItemId, isFavorite) {
  if (demoMode) {
    const item = demoFeed.find((i) => i.id === feedItemId)
    if (isFavorite) demoFavorites.add(item.news.id)
    else demoFavorites.delete(item.news.id)
    return { id: feedItemId, is_favorite: isFavorite }
  }
  return request(`/api/feed/${feedItemId}/favorite`, {
    method: 'POST',
    token,
    body: { is_favorite: isFavorite },
  })
}

export function logout() {
  setToken(null)
  demoMode = false
  demoFeed = null
  demoFavorites = new Set()
}
