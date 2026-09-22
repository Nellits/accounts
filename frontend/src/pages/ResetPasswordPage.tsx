import { FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { resetPassword, validateResetToken } from "../api";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [tokenOk, setTokenOk] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!token) {
        setTokenOk(false);
        setError("Missing reset token");
        return;
      }
      try {
        await validateResetToken(token);
        if (!cancelled) setTokenOk(true);
      } catch (err) {
        if (!cancelled) {
          setTokenOk(false);
          setError(err instanceof Error ? err.message : "Invalid link");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const out = await resetPassword(token, password);
      setMessage(out.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Choose a new password</h1>
      {tokenOk === false && error && <div className="error">{error}</div>}
      {tokenOk && !message && (
        <form onSubmit={onSubmit}>
          <label htmlFor="password">New password</label>
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
            {busy ? "Saving…" : "Update password"}
          </button>
        </form>
      )}
      {message && <div className="ok">{message}</div>}
      <div className="links">
        <Link to="/login">Back to sign in</Link>
      </div>
    </>
  );
}
