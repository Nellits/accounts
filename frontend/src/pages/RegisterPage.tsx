import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { afterAuthRedirect, register, safeRedirect } from "../api";

export default function RegisterPage() {
  const [params] = useSearchParams();
  const redirectUri = params.get("redirect_uri");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await register(email, password, name || undefined);
      afterAuthRedirect(redirectUri);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
      setBusy(false);
    }
  }

  const q = safeRedirect(redirectUri)
    ? `?redirect_uri=${encodeURIComponent(safeRedirect(redirectUri)!)}`
    : "";

  return (
    <>
      <h1>Create account</h1>
      <form onSubmit={onSubmit}>
        <label htmlFor="name">Name</label>
        <input id="name" value={name} onChange={(e) => setName(e.target.value)} />
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
          autoComplete="new-password"
          required
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      <div className="links">
        <Link to={`/login${q}`}>Already have an account? Sign in</Link>
      </div>
    </>
  );
}
