const API = "/api";

export type User = {
  id: number;
  email: string | null;
  name: string | null;
};

async function parseError(res: Response): Promise<string> {
  const err = (await res.json().catch(() => ({}))) as { detail?: unknown };
  if (typeof err.detail === "string") return err.detail;
  return res.statusText;
}

export async function login(email: string, password: string): Promise<User> {
  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function register(email: string, password: string, name?: string): Promise<User> {
  const res = await fetch(`${API}/auth/register`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function me(): Promise<User> {
  const res = await fetch(`${API}/auth/me`, { credentials: "include" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function forgotPassword(email: string): Promise<{ message: string }> {
  const res = await fetch(`${API}/auth/forgot-password`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function validateResetToken(token: string): Promise<void> {
  const res = await fetch(
    `${API}/auth/reset-password/validate?token=${encodeURIComponent(token)}`
  );
  if (!res.ok) throw new Error(await parseError(res));
}

export async function resetPassword(token: string, password: string): Promise<{ message: string }> {
  const res = await fetch(`${API}/auth/reset-password`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, password }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

/** Soft check for absolute http(s) URLs; server /api/auth/redirect is authoritative. */
export function safeRedirect(redirectUri: string | null): string | null {
  if (!redirectUri) return null;
  try {
    const u = new URL(redirectUri);
    if (u.protocol === "http:" || u.protocol === "https:") {
      return redirectUri;
    }
  } catch {
    return null;
  }
  return null;
}

export function afterAuthRedirect(redirectUri: string | null) {
  if (!redirectUri) {
    window.location.href = "/login";
    return;
  }
  // Server enforces AUTH_COOKIE_DOMAIN / AUTH_REDIRECT_ALLOWLIST
  window.location.href = `/api/auth/redirect?redirect_uri=${encodeURIComponent(redirectUri)}`;
}
