import { Link, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Login from "./pages/Login";
import Lobby from "./pages/Lobby";
import Room from "./pages/Room";
import Account from "./pages/Account";

function Private({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="center">Loading…</div>;
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const { user, logout } = useAuth();
  return (
    <>
      <header className="topbar">
        <Link to="/" className="logo">🎲 Ludo Royale</Link>
        {user && (
          <nav>
            <Link to="/account">{user.username}</Link>
            <button className="link" onClick={logout}>Logout</button>
          </nav>
        )}
      </header>
      <main>
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
          <Route path="/" element={<Private><Lobby /></Private>} />
          <Route path="/account" element={<Private><Account /></Private>} />
          <Route path="/room/:code" element={<Private><Room /></Private>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
