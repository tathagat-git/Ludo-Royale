import { useMemo } from "react";
import { ARM_COLORS, CELL, buildBoard, piecePoint } from "../lib/geometry";

const cellRect = (cell, fill, extra = {}) => (
  <rect x={-CELL / 2 + 1} y={-CELL / 2 + 1} width={CELL - 2} height={CELL - 2} rx="4" fill={fill}
    stroke="#1b1f2a" strokeWidth="1.5" transform={`translate(${cell.x} ${cell.y}) rotate(${cell.rot})`} {...extra} />
);

export default function Board({ state, pieces, myTurnSeat, onMove }) {
  const board = useMemo(() => buildBoard(state.arms), [state.arms]);
  const e = board.extent;
  const R = board.ringLen;

  // group pieces by location so stacked pieces can be fanned out
  const items = [];
  state.seats.forEach((seat) => {
    pieces[seat.seat].forEach((pos, idx) => {
      const [x, y] = piecePoint(board, seat.arm, pos, idx);
      items.push({ key: `${seat.seat}-${idx}`, seat, idx, pos, x, y });
    });
  });
  const groups = {};
  items.forEach((it) => { const k = `${Math.round(it.x)},${Math.round(it.y)}`; (groups[k] ||= []).push(it); });
  Object.values(groups).forEach((g) => {
    if (g.length > 1 && g[0].pos !== -1 && g[0].pos !== R + 4) {
      g.forEach((it, i) => { it.x += (i - (g.length - 1) / 2) * 9; it.y += (i % 2 ? 4 : -4); });
    }
  });

  const legal = myTurnSeat !== null && state.turn === myTurnSeat ? state.legal : [];
  const movable = new Set(legal.map((m) => m.piece));
  const markers = [];
  const seen = new Set();
  const turnSeat = state.seats[state.turn];
  legal.forEach((m) => {
    const from = state.pieces[myTurnSeat][m.piece];
    const key = `${from}-${m.dir}`;
    if (seen.has(key)) return;
    seen.add(key);
    const [x, y] = piecePoint(board, turnSeat.arm, m.to, m.piece);
    markers.push({ ...m, x, y, key });
  });

  const clickPiece = (it) => {
    if (it.seat.seat !== myTurnSeat) return;
    const m = legal.find((l) => l.piece === it.idx && l.dir === "f") || legal.find((l) => l.piece === it.idx);
    if (m) onMove(m.piece, m.dir);
  };

  return (
    <svg className="board" viewBox={`${-e} ${-e} ${2 * e} ${2 * e}`}>
      <defs>
        <radialGradient id="pg" cx="35%" cy="30%"><stop offset="0" stopColor="#fff" stopOpacity=".75" /><stop offset="1" stopColor="#fff" stopOpacity="0" /></radialGradient>
      </defs>
      <rect x={-e} y={-e} width={2 * e} height={2 * e} rx="24" fill="#10131c" />
      {board.yards.map((y, k) => {
        const used = state.seats.some((s) => s.arm === k);
        return (
          <g key={k} opacity={used ? 1 : 0.25}>
            <circle cx={y.cx} cy={y.cy} r={y.r} fill={ARM_COLORS[k]} fillOpacity=".25" stroke={ARM_COLORS[k]} strokeWidth="3" />
            {y.slots.map(([sx, sy], i) => <circle key={i} cx={sx} cy={sy} r={CELL * 0.45} fill="#0b0e15" fillOpacity=".55" />)}
          </g>
        );
      })}
      {board.triangles.map((t) => <polygon key={t.arm} points={t.pts.map((p) => p.join(",")).join(" ")} fill={ARM_COLORS[t.arm]} stroke="#10131c" strokeWidth="2" />)}
      {board.ring.map((c, i) => {
        const startArm = i % 13 === 8 ? c.arm : -1;
        const isSafe = board.safe.has(i);
        return (
          <g key={i}>
            {cellRect(c, startArm >= 0 ? ARM_COLORS[startArm] : "#f4f5f7")}
            {isSafe && startArm < 0 && <text x={c.x} y={c.y + 6} textAnchor="middle" fontSize="18" fill="#8a8f9c">★</text>}
          </g>
        );
      })}
      {board.lane.map((l, k) => l.map((c, i) => <g key={`${k}-${i}`}>{cellRect(c, ARM_COLORS[k], { fillOpacity: 0.85 })}</g>))}

      {markers.map((m) => (
        <g key={m.key} className="marker" onClick={() => onMove(m.piece, m.dir)}>
          <circle cx={m.x} cy={m.y} r={CELL * 0.5} fill={m.dir === "b" ? "#ff9800" : "#4caf50"} fillOpacity=".35"
            stroke={m.dir === "b" ? "#ff9800" : "#4caf50"} strokeWidth="3" strokeDasharray={m.dir === "b" ? "5 4" : "0"} />
          <text x={m.x} y={m.y + 5} textAnchor="middle" fontSize="15" fill="#fff" pointerEvents="none">{m.dir === "b" ? "◀" : "▶"}</text>
        </g>
      ))}

      {items.map((it) => (
        <g key={it.key} className={`piece ${movable.has(it.idx) && it.seat.seat === myTurnSeat ? "movable" : ""}`}
          style={{ transform: `translate(${it.x}px, ${it.y}px)` }} onClick={() => clickPiece(it)}>
          <circle r={CELL * 0.34} fill={ARM_COLORS[it.seat.arm]} stroke="#fff" strokeWidth="2.5" />
          <circle r={CELL * 0.34} fill="url(#pg)" />
          <circle r={CELL * 0.1} fill="#fff" fillOpacity=".85" />
        </g>
      ))}
    </svg>
  );
}
