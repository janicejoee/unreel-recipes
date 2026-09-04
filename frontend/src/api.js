const SESSION_KEY = "unreel_session";
const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

function api(path) {
  return `${API_URL}${path}`;
}

export function getSession() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
  } catch {
    return null;
  }
}

export function setSession(session) {
  if (!session) localStorage.removeItem(SESSION_KEY);
  else localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export async function refreshSession() {
  const session = getSession();
  if (!session?.refresh_token) {
    setSession(null);
    return null;
  }

  const response = await fetch(api("/auth/refresh"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: session.refresh_token }),
  });

  if (!response.ok) {
    setSession(null);
    return null;
  }

  const next = await response.json();
  setSession(next);
  return next;
}

export async function authFetch(url, options = {}, retry = true) {
  const session = getSession();
  const headers = new Headers(options.headers || {});
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }

  const response = await fetch(api(url), { ...options, headers });
  if (response.status === 401 && retry && session?.refresh_token) {
    const refreshed = await refreshSession();
    if (refreshed) return authFetch(url, options, false);
  }
  return response;
}

export async function login(email, password) {
  const response = await fetch(api("/auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Could not sign in.");
  setSession(data);
  return data;
}

export async function signup(email, password) {
  const response = await fetch(api("/auth/signup"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Could not create an account.");
  setSession(data);
  return data;
}

export async function loadUser() {
  const session = getSession();
  if (!session?.access_token) return null;
  const response = await authFetch("/auth/me", { headers: { Accept: "application/json" } });
  if (!response.ok) {
    setSession(null);
    return null;
  }
  const data = await response.json();
  return data.user ?? null;
}

export function logout() {
  setSession(null);
}
