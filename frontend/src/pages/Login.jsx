import { useState } from "react";
import { useAuth } from "../auth";

export default function Login() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ username: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      if (mode === "login") await login(f.username, f.password);
      else await register(f.username, f.email, f.password);
    } catch (x) { setErr(x.message); } finally { setBusy(false); }
  };

  return (
    <form className="card auth" onSubmit={submit}>
      <h2>{mode === "login" ? "Welcome back" : "Create account"}</h2>
      <input placeholder={mode === "login" ? "Username or email" : "Username (3-20, letters/numbers/_)"} value={f.username} onChange={set("username")} required autoFocus />
      {mode === "register" && <input type="email" placeholder="Email" value={f.email} onChange={set("email")} required />}
      <input type="password" placeholder="Password (min 8 chars)" value={f.password} onChange={set("password")} required />
      {err && <p className="error">{err}</p>}
      <button className="primary" disabled={busy}>{busy ? "…" : mode === "login" ? "Login" : "Sign up"}</button>
      <button type="button" className="link" onClick={() => { setMode(mode === "login" ? "register" : "login"); setErr(""); }}>
        {mode === "login" ? "New here? Create an account" : "Have an account? Login"}
      </button>
    </form>
  );
}
