/**
 * Browser helpers for Accounts (shared cookie SSO across sibling apps).
 *
 * Configure via:
 *   VITE_ACCOUNTS_URL=https://accounts.example.com
 */

export type AuthUser = {
  id: number;
  email: string | null;
  name: string | null;
  has_password?: boolean;
  avatar_url?: string | null;
  theme?: "light" | "dark" | null;
  is_admin?: boolean;
};

function accountsBase(): string {
  const raw =
    (typeof import.meta !== "undefined" &&
      (import.meta as ImportMeta & { env?: Record<string, string> }).env?.VITE_ACCOUNTS_URL) ||
    (typeof process !== "undefined" && process.env?.VITE_ACCOUNTS_URL) ||
    "";
  if (!raw) {
    throw new Error("VITE_ACCOUNTS_URL is required");
  }
  return raw.replace(/\/$/, "");
}

async function parseError(res: Response): Promise<string> {
  const err = (await res.json().catch(() => ({}))) as { detail?: unknown };
  if (typeof err.detail === "string") return err.detail;
  return res.statusText;
}

export function loginUrl(redirectUri?: string): string {
  const base = `${accountsBase()}/login`;
  if (!redirectUri) return base;
  return `${base}?redirect_uri=${encodeURIComponent(redirectUri)}`;
}

export function redirectToLogin(redirectUri?: string): void {
  const uri = redirectUri ?? (typeof window !== "undefined" ? window.location.href : undefined);
  window.location.href = loginUrl(uri);
}

export async function getMe(): Promise<AuthUser> {
  const res = await fetch(`${accountsBase()}/api/auth/me`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const res = await fetch(`${accountsBase()}/api/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function register(
  email: string,
  password: string,
  name?: string
): Promise<AuthUser> {
  const res = await fetch(`${accountsBase()}/api/auth/register`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function logout(): Promise<void> {
  await fetch(`${accountsBase()}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
}

export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<AuthUser> {
  const res = await fetch(`${accountsBase()}/api/auth/change-password`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function forgotPassword(email: string): Promise<{ message: string }> {
  const res = await fetch(`${accountsBase()}/api/auth/forgot-password`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function updateMe(payload: {
  name?: string;
  theme?: "light" | "dark";
}): Promise<AuthUser> {
  const res = await fetch(`${accountsBase()}/api/auth/me`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

/** Absolute avatar URL when avatar_url is a path on the accounts host. */
export function avatarAbsoluteUrl(avatarUrl: string | null | undefined): string | null {
  if (!avatarUrl) return null;
  if (avatarUrl.startsWith("http://") || avatarUrl.startsWith("https://")) return avatarUrl;
  return `${accountsBase()}${avatarUrl.startsWith("/") ? "" : "/"}${avatarUrl}`;
}
