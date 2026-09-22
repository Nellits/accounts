import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const out = await forgotPassword(email);
      setMessage(out.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Reset password</h1>
      <form onSubmit={onSubmit}>
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        {error && <div className="error">{error}</div>}
        {message && <div className="ok">{message}</div>}
        <button type="submit" disabled={busy}>
          {busy ? "Sending…" : "Send reset link"}
        </button>
      </form>
      <div className="links">
        <Link to="/login">Back to sign in</Link>
      </div>
    </>
  );
}
