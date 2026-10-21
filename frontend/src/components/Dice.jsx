const PIPS = {
  1: [[1, 1]], 2: [[0, 0], [2, 2]], 3: [[0, 0], [1, 1], [2, 2]], 4: [[0, 0], [2, 0], [0, 2], [2, 2]],
  5: [[0, 0], [2, 0], [1, 1], [0, 2], [2, 2]], 6: [[0, 0], [2, 0], [0, 1], [2, 1], [0, 2], [2, 2]],
};

export default function Dice({ value, rollKey, color, canRoll, onRoll }) {
  return (
    <div className="dice-wrap">
      <button className={`dice ${canRoll ? "ready" : ""}`} disabled={!canRoll} onClick={onRoll} style={{ "--c": color }} key={rollKey}>
        <svg viewBox="0 0 60 60" width="64" height="64" className="die-face">
          <rect x="3" y="3" width="54" height="54" rx="10" fill="#fff" stroke={color} strokeWidth="3" />
          {(PIPS[value] || []).map(([cx, cy], i) => <circle key={i} cx={14 + cx * 16} cy={14 + cy * 16} r="5" fill="#222" />)}
          {!value && <text x="30" y="38" textAnchor="middle" fontSize="22" fill="#999">?</text>}
        </svg>
      </button>
      <small>{canRoll ? "Your turn - roll!" : "\u00a0"}</small>
    </div>
  );
}
