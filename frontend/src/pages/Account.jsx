import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

export default function Account() {
  const { user } = useAuth();
  const [f, setF] = useState({ current: "", next: "", again: "" });
  const [msg, setMsg] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    if (f.next !== f.again) return setMsg({ error: true, text: "New passwords do not match" });
    try {
      await api("/auth/change-password", { method: "POST", body: { current_password: f.current, new_password: f.next } });
      setMsg({ text: "Password changed ✅" });
      setF({ current: "", next: "", again: "" });
    } catch (x) { setMsg({ error: true, text: x.message }); }
  };
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  return (
    <form className="card auth" onSubmit={submit}>
      <h2>Account</h2>
      <p className="muted">{user.username} · {user.email}</p>
      <input type="password" placeholder="Current password" value={f.current} onChange={set("current")} required />
      <input type="password" placeholder="New password (min 8)" value={f.next} onChange={set("next")} required minLength={8} />
      <input type="password" placeholder="Repeat new password" value={f.again} onChange={set("again")} required />
      {msg && <p className={msg.error ? "error" : "ok"}>{msg.text}</p>}
      <button className="primary">Change password</button>
    </form>
  );
}
