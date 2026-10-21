import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

// Friends list, requests, search. If `roomCode` is passed, each friend gets an Invite button.
export default function Friends({ roomCode, memberIds = [] }) {
  const [friends, setFriends] = useState([]);
  const [reqs, setReqs] = useState([]);
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [note, setNote] = useState("");

  const load = useCallback(() => {
    api("/friends").then(setFriends).catch(() => {});
    api("/friends/requests").then(setReqs).catch(() => {});
  }, []);
  useEffect(() => { load(); const t = setInterval(load, 6000); return () => clearInterval(t); }, [load]);

  useEffect(() => {
    if (q.trim().length < 2) return setResults([]);
    const t = setTimeout(() => api(`/friends/search?q=${encodeURIComponent(q)}`).then(setResults).catch(() => {}), 250);
    return () => clearTimeout(t);
  }, [q]);

  const act = async (fn, okText) => {
    try { await fn(); setNote(okText || ""); } catch (e) { setNote(e.message); }
    load();
    if (q) api(`/friends/search?q=${encodeURIComponent(q)}`).then(setResults).catch(() => {});
  };

  return (
    <div className="card friends">
      <h3>Friends</h3>
      <input placeholder="Search players to add…" value={q} onChange={(e) => setQ(e.target.value)} />
      {results.map((u) => (
        <div className="row" key={u.id}>
          <span>{u.username}</span>
          {u.relation === "none" && <button onClick={() => act(() => api("/friends/request", { method: "POST", body: { username: u.username } }), "Request sent")}>Add</button>}
          {u.relation === "sent" && <span className="muted">Requested</span>}
          {u.relation === "friends" && <span className="muted">Friend</span>}
          {u.relation === "received" && <button onClick={() => act(() => api("/friends/request", { method: "POST", body: { username: u.username } }), "Friend added")}>Accept</button>}
        </div>
      ))}
      {reqs.length > 0 && <h4>Requests</h4>}
      {reqs.map((r) => (
        <div className="row" key={r.id}>
          <span>{r.from_user.username}</span>
          <span>
            <button className="primary" onClick={() => act(() => api(`/friends/requests/${r.id}/accept`, { method: "POST" }))}>Accept</button>{" "}
            <button onClick={() => act(() => api(`/friends/requests/${r.id}/decline`, { method: "POST" }))}>Decline</button>
          </span>
        </div>
      ))}
      <h4>My friends ({friends.length})</h4>
      {friends.length === 0 && <p className="muted">No friends yet — search above.</p>}
      {friends.map((f) => (
        <div className="row" key={f.id}>
          <span>{f.username}</span>
          <span>
            {roomCode && !memberIds.includes(f.id) && (
              <button className="primary" onClick={() => act(() => api(`/rooms/${roomCode}/invite`, { method: "POST", body: { user_id: f.id } }), `Invited ${f.username}`)}>Invite</button>
            )}{" "}
            <button className="link" title="Remove friend" onClick={() => confirm(`Remove ${f.username}?`) && act(() => api(`/friends/${f.id}`, { method: "DELETE" }))}>✕</button>
          </span>
        </div>
      ))}
      {note && <p className="muted">{note}</p>}
    </div>
  );
}
