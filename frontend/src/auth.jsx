import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) return setReady(true);
    api("/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setReady(true));
  }, []);

  const finish = (r) => { setToken(r.access_token); setUser(r.user); };
  const value = {
    user, ready,
    login: async (identifier, password) => finish(await api("/auth/login", { method: "POST", body: { identifier, password } })),
    register: async (username, email, password) => finish(await api("/auth/register", { method: "POST", body: { username, email, password } })),
    logout: () => { setToken(null); setUser(null); },
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
