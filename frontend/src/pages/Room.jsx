import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, wsUrl } from "../api";
import { useAuth } from "../auth";
import Board from "../components/Board";
import Chat from "../components/Chat";
import Dice from "../components/Dice";
import Friends from "../components/Friends";
import { ARM_COLORS } from "../lib/geometry";
import useAnimatedPieces from "../lib/useAnimatedPieces";

export default function Room() {
  const { code: rawCode } = useParams();
  const code = rawCode.toUpperCase();
  const { user } = useAuth();
  const nav = useNavigate();
  const [room, setRoom] = useState(null);
  const [online, setOnline] = useState([]);
  const [state, setState] = useState(null);
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState("connecting");
  const [error, setError] = useState("");
  const [left, setLeft] = useState(null);
  const deadline = useRef({ at: null, offset: 0 });
  const ws = useRef(null);
  const pieces = useAnimatedPieces(state);

  const send = useCallback((msg) => ws.current?.readyState === 1 && ws.current.send(JSON.stringify(msg)), []);

  useEffect(() => {
    let closed = false, retry = 0, timer;
    const connect = async () => {
      try { await api(`/rooms/${code}/join`, { method: "POST" }); }   // idempotent: lets shared links work
      catch (e) { setError(e.message); setStatus("closed"); return; }
      const sock = new WebSocket(wsUrl(code));
      ws.current = sock;
      sock.onopen = () => { retry = 0; setStatus("online"); };
      sock.onmessage = (ev) => {
        const m = JSON.parse(ev.data);
        if (m.type === "history") setMessages(m.messages);
        else if (m.type === "chat") setMessages((p) => [...p, m.message]);
        else if (m.type === "room") { setRoom(m.room); setOnline(m.room.online || []); }
        else if (m.type === "state") {
          setState(m.state);
          deadline.current = { at: m.deadline, offset: m.server_time ? Date.now() / 1000 - m.server_time : 0 };
        } else if (m.type === "error") { setError(m.message); setTimeout(() => setError(""), 3000); }
      };
      sock.onclose = (ev) => {
        if (closed) return;
        if (ev.code === 4403) { setError("You are not a member of this room"); setStatus("closed"); return; }
        setStatus("reconnecting");
        timer = setTimeout(connect, Math.min(1000 * 2 ** retry++, 8000));
      };
    };
    connect();
    return () => { closed = true; clearTimeout(timer); ws.current?.close(); };
  }, [code]);

  useEffect(() => {
    const t = setInterval(() => {
      const { at, offset } = deadline.current;
      setLeft(at ? Math.max(0, Math.round(at - (Date.now() / 1000 - offset))) : null);
    }, 500);
    return () => clearInterval(t);
  }, []);

  if (!room) return <div className="center">{error || (status === "connecting" ? "Joining room…" : "Reconnecting…")}{status === "closed" && <p><button onClick={() => nav("/")}>Back</button></p>}</div>;

  const isHost = room.host_id === user.id;
  const playing = state && state.seats;
  const mySeat = playing ? state.seats.find((s) => s.user_id === user.id)?.seat ?? null : null;
  const turnSeat = playing ? state.seats[state.turn] : null;
  const myTurn = playing && state.status === "playing" && turnSeat.user_id === user.id;
  const canRoll = myTurn && state.dice === null;
  const copy = () => navigator.clipboard?.writeText(`${location.origin}/room/${code}`);
  const leave = async () => { if (!playing) await api(`/rooms/${code}/leave`, { method: "POST" }).catch(() => {}); nav("/"); };

  return (
    <div className="room">
      <div className="room-main">
        <div className="room-head">
          <span><b>{room.mode === "twisted" ? "Twisted ↔" : "Classic"}</b> · Room <code className="code" onClick={copy} title="Click to copy invite link">{code}</code></span>
          <span className={`pill ${status}`}>{status}</span>
          <button onClick={leave}>{playing ? "Exit" : "Leave"}</button>
        </div>

        {!playing && (
          <div className="card lobby">
            <h2>Waiting for players ({room.members.length}/{room.max_players})</h2>
            <div className="seats">
              {Array.from({ length: room.max_players }, (_, i) => {
                const m = room.members.find((x) => x.seat === i);
                return (
                  <div className="seat" key={i} style={{ borderColor: ARM_COLORS[i] }}>
                    {m ? <>{m.username}{m.user_id === room.host_id && " 👑"} <span className={online.includes(m.user_id) ? "dot on" : "dot"} /></> : <span className="muted">{room.fill_with_bots ? "🤖 Bot" : "Empty"}</span>}
                  </div>
                );
              })}
            </div>
            <p className="muted">Share code <b>{code}</b> or <button className="link" onClick={copy}>copy invite link</button>.</p>
            {isHost
              ? <button className="primary big" onClick={() => send({ type: "start" })} disabled={!room.fill_with_bots && room.members.length < 2}>Start game</button>
              : <p>Waiting for the host to start…</p>}
          </div>
        )}

        {playing && (
          <>
            <div className="turnbar" style={{ background: ARM_COLORS[turnSeat.arm] }}>
              {state.status === "finished"
                ? `🏆 ${state.seats[state.finished_order[0]].name} wins!`
                : <>{myTurn ? "Your turn" : `${turnSeat.name}'s turn`}{left !== null && <b> · {left}s</b>}</>}
            </div>
            <Board state={state} pieces={pieces} myTurnSeat={mySeat} onMove={(piece, dir) => send({ type: "move", piece, dir })} />
          </>
        )}
        {error && <div className="toast">{error}</div>}
      </div>

      <aside className="room-side">
        {playing && (
          <div className="card">
            <div className="players">
              {state.seats.map((s) => {
                const rank = state.finished_order.indexOf(s.seat);
                return (
                  <div key={s.seat} className={`player ${s.seat === state.turn && state.status === "playing" ? "active" : ""}`}>
                    <span className="swatch" style={{ background: ARM_COLORS[s.arm] }} />
                    <span>{s.name}{s.is_bot && " 🤖"}{s.user_id === user.id && " (you)"}</span>
                    <small>{rank >= 0 ? `#${rank + 1}` : `${state.pieces[s.seat].filter((p) => p === state.arms * 13 + 4).length}/4 home`}</small>
                  </div>
                );
              })}
            </div>
            <Dice value={state.last_roll?.value} rollKey={`${state.last_roll?.seat}-${state.move_no}-${state.last_event}`}
              color={ARM_COLORS[(state.last_roll ? state.seats[state.last_roll.seat] : turnSeat).arm]} canRoll={canRoll} onRoll={() => send({ type: "roll" })} />
            <p className="event">{state.last_event}</p>
            {state.status === "finished" && <button className="primary" onClick={() => nav("/")}>Back to lobby</button>}
          </div>
        )}
        {!playing && <Friends roomCode={code} memberIds={room.members.map((m) => m.user_id)} />}
        <div className="card"><h3>Chat</h3><Chat messages={messages} meId={user.id} onSend={(text) => send({ type: "chat", text })} /></div>
      </aside>
    </div>
  );
}
