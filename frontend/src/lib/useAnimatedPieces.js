import { useEffect, useRef, useState } from "react";

// Steps the moved piece cell-by-cell so it walks along the track instead of teleporting.
export default function useAnimatedPieces(state) {
  const [shown, setShown] = useState(null);
  const lastNo = useRef(-1);
  const timer = useRef(null);

  useEffect(() => () => clearInterval(timer.current), []);
  useEffect(() => {
    if (!state) return;
    clearInterval(timer.current);
    const target = state.pieces.map((r) => [...r]);
    const lm = state.last_move;
    const consecutive = lastNo.current >= 0 && state.move_no - lastNo.current === 1;
    lastNo.current = state.move_no;
    if (!lm || !consecutive || lm.from === -1) return setShown(target);
    const { seat, piece, from, to } = lm;
    const step = to > from ? 1 : -1;
    let cur = from;
    const frame = (c) => { const n = target.map((r) => [...r]); n[seat][piece] = c; return n; };
    setShown(frame(cur));
    timer.current = setInterval(() => {
      cur += step;
      setShown(frame(cur));
      if (cur === to) { clearInterval(timer.current); setShown(target); }
    }, 160);
  }, [state?.move_no, state?.status]); // eslint-disable-line

  return shown && state && shown.length === state.pieces.length ? shown : state?.pieces;
}
