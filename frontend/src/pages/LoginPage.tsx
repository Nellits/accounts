import { FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { afterAuthRedirect, login, me, safeRedirect } from "../api";

export default function LoginPage() {
  const [params] = useSearchParams();
  const redirectUri = params.get("redirect_uri");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await me();
        if (!cancelled) afterAuthRedirect(redirectUri);
      } catch {
        /* not logged in */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [redirectUri]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      afterAuthRedirect(redirectUri);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      setBusy(false);
    }
  }

  const q = safeRedirect(redirectUri)
    ? `?redirect_uri=${encodeURIComponent(safeRedirect(redirectUri)!)}`
    : "";

  return (
    <>
      <h1>Sign in</h1>
      <form onSubmit={onSubmit}>
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <div className="links">
        <div>
          <Link to={`/register${q}`}>Create an account</Link>
        </div>
        <div>
          <Link to="/forgot-password">Forgot password?</Link>
        </div>
      </div>
    </>
  );
}
