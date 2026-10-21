// Небольшой браузерный клиент без сторонних библиотек.
// Один экземпляр createApi хранит один токен в памяти до перезагрузки страницы.
export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function createApi(baseUrl = "http://localhost:8000") {
  let accessToken = null;
  const base = baseUrl.replace(/\/+$/, "");

  async function request(path, { method = "GET", body } = {}) {
    const headers = {};
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetch(`${base}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) throw new ApiError(response.status, data.detail ?? data);
    return data;
  }

  async function startSession(path, body) {
    const session = await request(path, { method: "POST", body });
    accessToken = session.access_token;
    return session;
  }

  return {
    login: (email, password) => startSession("/api/auth/login", { email, password }),
    register: (body) => startSession("/api/auth/register", body),
    clearToken: () => { accessToken = null; },
    me: () => request("/api/auth/me"),
    companies: () => request("/api/companies"),
    feed: (params = {}) => {
      const values = Object.entries(params).filter(([, value]) => value != null);
      return request(`/api/feed?${new URLSearchParams(values)}`);
    },
    detail: (id) => request(`/api/feed/${encodeURIComponent(id)}`),
    setFavorite: (id, value) => request(`/api/feed/${encodeURIComponent(id)}/favorite`, {
      method: "POST", body: { is_favorite: value },
    }),
    ask: (id, question) => request(`/api/feed/${encodeURIComponent(id)}/ask`, {
      method: "POST", body: { question },
    }),
  };
}
