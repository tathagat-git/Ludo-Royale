import { useEffect, useRef, useState } from "react";

export default function Chat({ messages, meId, onSend }) {
  const [text, setText] = useState("");
  const box = useRef(null);
  useEffect(() => { box.current?.scrollTo(0, box.current.scrollHeight); }, [messages.length]);
  const submit = (e) => { e.preventDefault(); if (text.trim()) { onSend(text); setText(""); } };
  return (
    <div className="chat">
      <div className="msgs" ref={box}>
        {messages.length === 0 && <p className="muted">Say hi 👋</p>}
        {messages.map((m) => (
          <div key={m.id} className={m.user_id === meId ? "msg me" : "msg"}><b>{m.username}</b> {m.text}</div>
        ))}
      </div>
      <form onSubmit={submit}>
        <input value={text} maxLength={300} placeholder="Type a message…" onChange={(e) => setText(e.target.value)} />
        <button className="primary">Send</button>
      </form>
    </div>
  );
}
