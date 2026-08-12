import { Navigate, Route, Routes, useSearchParams } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";

function RedirectHome() {
  const [params] = useSearchParams();
  const redirect = params.get("redirect_uri");
  const q = redirect ? `?redirect_uri=${encodeURIComponent(redirect)}` : "";
  return <Navigate to={`/login${q}`} replace />;
}

export default function App() {
  return (
    <div className="shell">
      <header className="brand">
        <span className="logo">N</span>
        <div>
          <strong>Nellits</strong>
          <div className="muted">One account for all apps</div>
        </div>
      </header>
      <main className="card">
        <Routes>
          <Route path="/" element={<RedirectHome />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="*" element={<RedirectHome />} />
        </Routes>
      </main>
    </div>
  );
}
