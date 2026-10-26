// API-клиент к 02-backend с автоматическим переключением в автономный демо-режим,
// если backend недоступен (например, на статическом GitHub Pages).
import { DEMO_COMPANIES, buildDemoFeed, demoUser } from "./demoData";

const TOKEN_KEY = "alfa_news_token";
const STATIC_DEMO = import.meta.env.VITE_DEMO_MODE === "true";
// Лента и профиль — быстрые запросы; чат ждёт ответ LLM (backend: 130 с, nginx: 120 с).
const DEFAULT_TIMEOUT_MS = 20_000;
const CHAT_TIMEOUT_MS = 125_000;
// Backend отдаёт ленту постранично; на экране показываем всё целиком.
const FEED_PAGE_SIZE = 100;

export const MESSAGES = {
  network: "Нет связи с сервером. Проверьте подключение и повторите попытку.",
  timeout: "Сервер отвечает слишком долго. Попробуйте ещё раз через минуту.",
  server: "Сервис временно недоступен. Повторите попытку чуть позже.",
  unauthorized: "Сессия истекла. Войдите снова.",
  forbidden: "У вас нет доступа к этим данным.",
  notFound: "Запрошенные данные не найдены.",
  generic: "Что-то пошло не так. Повторите попытку.",
};

let demoMode = getToken() === "demo";
let demoFeed = demoMode ? buildDemoFeed() : null;
let demoFavorites = new Set();
let unauthorizedHandler = null;

export class ApiError extends Error {
  constructor(message, { status = 0, code = "generic", detail = "" } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

/** Регистрирует обработчик 401: приложение сбрасывает сессию в одном месте. */
export function onUnauthorized(handler) {
  unauthorizedHandler = handler;
}

function isNetworkError(err) {
  return err instanceof TypeError || err?.name === "TypeError";
}

function isAbortError(err) {
  return err?.name === "AbortError" || err?.name === "TimeoutError";
}

function extractDetail(data) {
  if (!data?.detail) return "";
  if (typeof data.detail === "string") return data.detail;
  // Ошибки валидации FastAPI приходят массивом {loc, msg}.
  if (Array.isArray(data.detail))
    return data.detail
      .map((entry) => entry?.msg)
      .filter(Boolean)
      .join(" ");
  return "";
}

function errorForStatus(status, detail) {
  if (status === 401)
    return new ApiError(MESSAGES.unauthorized, {
      status,
      code: "unauthorized",
      detail,
    });
  if (status === 403)
    return new ApiError(detail || MESSAGES.forbidden, {
      status,
      code: "forbidden",
      detail,
    });
  if (status === 404)
    return new ApiError(detail || MESSAGES.notFound, {
      status,
      code: "not_found",
      detail,
    });
  if (status === 504 || status === 408)
    return new ApiError(MESSAGES.timeout, { status, code: "timeout", detail });
  if (status >= 500)
    return new ApiError(MESSAGES.server, { status, code: "server", detail });
  return new ApiError(detail || MESSAGES.generic, {
    status,
    code: "client",
    detail,
  });
}

async function request(
  path,
  {
    method = "GET",
    token,
    body,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    skipAuthHandler = false,
  } = {},
) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err) {
    if (isAbortError(err))
      throw new ApiError(MESSAGES.timeout, { code: "timeout" });
    if (isNetworkError(err))
      throw new ApiError(MESSAGES.network, { code: "network" });
    throw err;
  }
  if (!response.ok) {
    let detail = "";
    try {
      detail = extractDetail(await response.json());
    } catch {
      /* тело не JSON (например, страница nginx 502) — оставляем общий текст */
    }
    const error = errorForStatus(response.status, detail);
    if (error.code === "unauthorized" && !skipAuthHandler && unauthorizedHandler)
      unauthorizedHandler(error);
    throw error;
  }
  try {
    return await response.json();
  } catch {
    throw new ApiError(MESSAGES.server, {
      status: response.status,
      code: "server",
    });
  }
}

export function isDemo() {
  return demoMode;
}

export function getToken() {
  try {
    return typeof window !== "undefined"
      ? window.localStorage.getItem(TOKEN_KEY)
      : null;
  } catch {
    return null;
  }
}

function setToken(token) {
  if (typeof window === "undefined") return;
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* приватный режим или заблокированное хранилище — сессия живёт до перезагрузки */
  }
}

function startDemo(email) {
  demoMode = true;
  demoFeed = buildDemoFeed();
  demoFavorites = new Set();
  const user = demoUser(email || "alfa-hack-2026");
  setToken("demo");
  return { access_token: "demo", token_type: "bearer", expires_in: 0, user };
}

function findDemoItem(feedItemId) {
  const item = demoFeed?.find((entry) => entry.id === feedItemId);
  if (!item)
    throw new ApiError(MESSAGES.notFound, { status: 404, code: "not_found" });
  return item;
}

export async function login(email, password) {
  if (STATIC_DEMO) return startDemo(email);
  try {
    const data = await request("/api/auth/login", {
      method: "POST",
      body: { email, password },
      skipAuthHandler: true,
    });
    setToken(data.access_token);
    demoMode = false;
    return data;
  } catch (err) {
    if (!(err instanceof ApiError)) throw err;
    if (["network", "server", "timeout"].includes(err.code)) {
      // Backend недоступен — включаем автономную демонстрацию.
      return startDemo(email);
    }
    if (err.code === "unauthorized")
      throw new ApiError(err.detail || "Неверный логин или пароль.", {
        status: 401,
        code: "credentials",
      });
    throw err;
  }
}

export async function getCompanies(token) {
  if (demoMode) return DEMO_COMPANIES;
  const data = await request("/api/companies", { token });
  return Array.isArray(data) ? data : [];
}

export async function getMe(token) {
  if (demoMode) return demoUser("alfa-hack-2026");
  return request("/api/auth/me", { token });
}

export async function getFeed(
  token,
  { company_id, role, favorites_only = false } = {},
) {
  if (demoMode) {
    return demoFeed
      .filter(
        (item) =>
          item.company_id === (company_id || "U_1595") &&
          item.role === (role || "CEO") &&
          (!favorites_only || demoFavorites.has(item.news.id)),
      )
      .sort((a, b) => b.importance_score - a.importance_score)
      .map((item) => ({
        ...item,
        is_favorite: demoFavorites.has(item.news.id),
      }));
  }
  const params = new URLSearchParams({ page_size: String(FEED_PAGE_SIZE) });
  if (company_id) params.set("company_id", company_id);
  if (role) params.set("role", role);
  if (favorites_only) params.set("favorites_only", "true");
  const data = await request(`/api/feed?${params}`, { token });
  return Array.isArray(data?.items) ? data.items : [];
}

export async function ask(token, feedItemId, question) {
  if (demoMode) {
    const item = findDemoItem(feedItemId);
    return {
      feed_item_id: feedItemId,
      answer:
        `Демо-ответ по карточке «${item.news.title}». Ваш вопрос: «${question}». ` +
        `${item.insight.why_it_matters} Рекомендуемый шаг: ${item.insight.action_item}`,
      is_demo: true,
      mode: null,
      sources: [],
    };
  }
  return request(`/api/feed/${encodeURIComponent(feedItemId)}/ask`, {
    method: "POST",
    token,
    body: { question },
    timeoutMs: CHAT_TIMEOUT_MS,
  });
}

export async function setFavorite(token, feedItemId, isFavorite) {
  if (demoMode) {
    const item = findDemoItem(feedItemId);
    if (isFavorite) demoFavorites.add(item.news.id);
    else demoFavorites.delete(item.news.id);
    return { id: feedItemId, is_favorite: isFavorite };
  }
  return request(`/api/feed/${encodeURIComponent(feedItemId)}/favorite`, {
    method: "POST",
    token,
    body: { is_favorite: isFavorite },
  });
}

export function logout() {
  setToken(null);
  demoMode = false;
  demoFeed = null;
  demoFavorites = new Set();
}
