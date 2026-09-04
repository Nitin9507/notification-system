export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
).replace(/\/$/, "");

const ACCESS_KEY = "ns.access";
const REFRESH_KEY = "ns.refresh";

export function getAccessToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function setTokens({ access, refresh }) {
  if (typeof window === "undefined") return;
  if (access) window.localStorage.setItem(ACCESS_KEY, access);
  if (refresh) window.localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

/** Turn DRF's nested error shapes into one readable line. */
function readError(data, status) {
  if (!data) return `Request failed (${status})`;
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  const first = Object.entries(data)[0];
  if (!first) return `Request failed (${status})`;
  const [field, value] = first;
  const text = Array.isArray(value) ? value[0] : value;
  return field === "non_field_errors" ? text : `${field}: ${text}`;
}

export function getRefreshToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

let refreshInFlight = null;

/** Swap the refresh token for a fresh access token, at most once at a time. */
async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_URL}/api/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (data?.access) {
          setTokens({ access: data.access });
          return data.access;
        }
        clearTokens();
        return null;
      })
      .catch(() => {
        clearTokens();
        return null;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

function request(path, method, body, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export async function apiFetch(path, { method = "GET", body, auth = true } = {}) {
  const token = auth ? getAccessToken() : null;
  let response = await request(path, method, body, token);

  // An expired access token is renewed once, transparently, before giving up.
  if (response.status === 401 && auth && token) {
    const fresh = await refreshAccessToken();
    if (fresh) response = await request(path, method, body, fresh);
  }

  if (response.status === 204) return null;

  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(readError(data, response.status), response.status, data);
  }
  return data;
}

export const api = {
  login: (username, password) =>
    apiFetch("/api/auth/login/", {
      method: "POST",
      body: { username, password },
      auth: false,
    }),
  register: (payload) =>
    apiFetch("/api/auth/register/", { method: "POST", body: payload, auth: false }),
  logout: () => apiFetch("/api/auth/logout/", { method: "POST" }),
  me: () => apiFetch("/api/auth/me/"),
  savePushSubscription: (id) =>
    apiFetch("/api/auth/push-subscription/", {
      method: "POST",
      body: { onesignal_player_id: id },
    }),
  savePhone: (phone) =>
    apiFetch("/api/auth/me/", {
      method: "PATCH",
      body: { profile: { phone_e164: phone } },
    }),

  matrix: () => apiFetch("/api/admin/matrix/"),
  createTrigger: (payload) =>
    apiFetch("/api/admin/triggers/", { method: "POST", body: payload }),
  toggleTrigger: (id, isActive) =>
    apiFetch(`/api/admin/triggers/${id}/toggle/`, {
      method: "PATCH",
      body: { is_active: isActive },
    }),
  saveTemplate: (triggerId, channel, payload) =>
    apiFetch(`/api/admin/triggers/${triggerId}/templates/${channel}/`, {
      method: "PUT",
      body: payload,
    }),
  deleteTemplate: (triggerId, channel) =>
    apiFetch(`/api/admin/triggers/${triggerId}/templates/${channel}/`, {
      method: "DELETE",
    }),
  toggleTemplate: (triggerId, channel, isEnabled) =>
    apiFetch(`/api/admin/triggers/${triggerId}/templates/${channel}/toggle/`, {
      method: "PATCH",
      body: { is_enabled: isEnabled },
    }),
  testSend: (triggerId, channel, recipient) =>
    apiFetch(`/api/admin/triggers/${triggerId}/templates/${channel}/test-send/`, {
      method: "POST",
      body: { recipient: recipient || "" },
    }),
  logs: (limit = 25) => apiFetch(`/api/admin/logs/?limit=${limit}`),
  events: () => apiFetch("/api/events/"),
  fireEvent: (code) => apiFetch(`/api/events/${code}/fire/`, { method: "POST", body: {} }),
};
