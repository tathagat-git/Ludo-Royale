import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import Friends from "../components/Friends";

export default function Lobby() {
  const nav = useNavigate();
  const [mode, setMode] = useState("classic");
  const [players, setPlayers] = useState(4);
  const [isPrivate, setPrivate] = useState(true);
  const [bots, setBots] = useState(true);
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");
  const [invites, setInvites] = useState([]);
  const [publicRooms, setPublicRooms] = useState([]);

  useEffect(() => {
    const load = () => {
      api("/invites").then(setInvites).catch(() => {});
      api("/rooms/public").then(setPublicRooms).catch(() => {});
    };
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  const guard = async (fn) => { setErr(""); try { await fn(); } catch (e) { setErr(e.message); } };
  const create = () => guard(async () => {
    const r = await api("/rooms", { method: "POST", body: { mode, max_players: players, is_private: isPrivate, fill_with_bots: bots } });
    nav(`/room/${r.code}`);
  });
  const join = (c) => guard(async () => { await api(`/rooms/${c.trim().toUpperCase()}/join`, { method: "POST" }); nav(`/room/${c.trim().toUpperCase()}`); });

  return (
    <div className="grid2">
      <div>
        {invites.map((i) => (
          <div className="card invite" key={i.id}>
            <span><b>{i.from_username}</b> invited you to a {i.mode} game</span>
            <span>
              <button className="primary" onClick={() => join(i.code)}>Join</button>{" "}
              <button onClick={() => api(`/invites/${i.id}/decline`, { method: "POST" }).then(() => setInvites(invites.filter((x) => x.id !== i.id)))}>Decline</button>
            </span>
          </div>
        ))}

        <div className="card">
          <h2>New game</h2>
          <div className="modes">
            <button className={mode === "classic" ? "mode active" : "mode"} onClick={() => setMode("classic")}>
              <b>Classic</b><small>Traditional rules. Pieces only move forward.</small>
            </button>
            <button className={mode === "twisted" ? "mode active" : "mode"} onClick={() => setMode("twisted")}>
              <b>Twisted ↔</b><small>Move forward or backward — but never behind your start cell.</small>
            </button>
          </div>
          <label>Players
            <div className="chips">
              {[2, 3, 4, 5, 6].map((n) => <button key={n} className={players === n ? "chip active" : "chip"} onClick={() => setPlayers(n)}>{n}</button>)}
            </div>
          </label>
          <label className="check"><input type="checkbox" checked={bots} onChange={(e) => setBots(e.target.checked)} /> Fill empty seats with bots</label>
          <label className="check"><input type="checkbox" checked={isPrivate} onChange={(e) => setPrivate(e.target.checked)} /> Private party (join with code / invite only)</label>
          <button className="primary big" onClick={create}>Create room</button>
        </div>

        <div className="card">
          <h3>Join with code</h3>
          <div className="row">
            <input placeholder="ABC123" value={code} maxLength={6} onChange={(e) => setCode(e.target.value.toUpperCase())} />
            <button className="primary" disabled={code.length !== 6} onClick={() => join(code)}>Join</button>
          </div>
          {err && <p className="error">{err}</p>}
        </div>

        <div className="card">
          <h3>Open rooms</h3>
          {publicRooms.length === 0 && <p className="muted">No public rooms right now.</p>}
          {publicRooms.map((r) => (
            <div className="row" key={r.code}>
              <span>{r.code} · {r.mode} · {r.members.length}/{r.max_players}</span>
              <button onClick={() => join(r.code)}>Join</button>
            </div>
          ))}
        </div>
      </div>
      <Friends />
    </div>
  );
}
