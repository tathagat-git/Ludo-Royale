// Board geometry for 4, 5 or 6 armed Ludo boards. Mirrors the rules in backend/app/services/game_engine.py
export const CELL = 40;
export const PER_ARM = 13;
export const START_J = 8;
export const STAR_OFFSET = 8;
export const ARM_COLORS = ["#e53935", "#43a047", "#fdd835", "#1e88e5", "#8e24aa", "#fb8c00"];
export const COLOR_BY_NAME = { red: ARM_COLORS[0], green: ARM_COLORS[1], yellow: ARM_COLORS[2], blue: ARM_COLORS[3], purple: ARM_COLORS[4], orange: ARM_COLORS[5] };

export function buildBoard(arms) {
  const c = CELL;
  const a = (3 * c) / (2 * Math.tan(Math.PI / arms));       // centre polygon apothem
  const vr = a / Math.cos(Math.PI / arms);                  // polygon vertex radius
  const theta = (k) => -Math.PI / 2 + (k * 2 * Math.PI) / arms;
  const pt = (k, u, v) => {
    const t = theta(k), r = a + (u - 0.5) * c;
    return [r * Math.cos(t) - v * c * Math.sin(t), r * Math.sin(t) + v * c * Math.cos(t)];
  };
  const ring = [];
  for (let k = 0; k < arms; k++) {
    for (let j = 0; j < PER_ARM; j++) {
      const [u, v] = j <= 5 ? [j + 1, -1] : j === 6 ? [6, 0] : [13 - j, 1];
      const [x, y] = pt(k, u, v);
      ring[k * PER_ARM + j] = { x, y, rot: (theta(k) * 180) / Math.PI, arm: k, j };
    }
  }
  const lane = [];
  for (let k = 0; k < arms; k++) {
    lane[k] = [];
    for (let i = 0; i < 5; i++) {
      const [x, y] = pt(k, 5 - i, 0);
      lane[k][i] = { x, y, rot: (theta(k) * 180) / Math.PI, arm: k };
    }
  }
  const vertex = (k) => { const t = theta(k) + Math.PI / arms; return [vr * Math.cos(t), vr * Math.sin(t)]; };
  const triangles = [];
  for (let k = 0; k < arms; k++) triangles.push({ arm: k, pts: [[0, 0], vertex((k - 1 + arms) % arms), vertex(k)] });

  const rho = vr + 4.2 * c;
  const yr = Math.min(2.4 * c, rho * Math.sin(Math.PI / arms) - 1.65 * c);
  const yards = [];
  for (let k = 0; k < arms; k++) {
    const t = theta(k) + Math.PI / arms;
    const cx = rho * Math.cos(t), cy = rho * Math.sin(t), o = yr * 0.42;
    yards[k] = { cx, cy, r: yr, slots: [[-o, -o], [o, -o], [-o, o], [o, o]].map(([dx, dy]) => [cx + dx, cy + dy]) };
  }
  const homeSlot = (k, i) => {
    const t = theta(k), r = vr * 0.5;
    const off = [[-0.25, -0.25], [0.25, -0.25], [-0.25, 0.25], [0.25, 0.25]][i].map((n) => n * c * 0.5);
    return [r * Math.cos(t) + off[0], r * Math.sin(t) + off[1]];
  };
  const extent = Math.max(a + 6 * c, rho + yr) + 0.6 * c;
  const ringLen = arms * PER_ARM;
  const safe = new Set();
  for (let k = 0; k < arms; k++) { safe.add((k * PER_ARM + START_J) % ringLen); safe.add((k * PER_ARM + START_J + STAR_OFFSET) % ringLen); }
  return { arms, ringLen, ring, lane, triangles, yards, homeSlot, extent, safe };
}

// where is piece `idx` of the seat sitting on arm `arm` at relative position `pos`?
export function piecePoint(board, arm, pos, idx) {
  const R = board.ringLen;
  if (pos === -1) return board.yards[arm].slots[idx];
  if (pos === R + 4) return board.homeSlot(arm, idx);
  if (pos <= R - 2) { const c = board.ring[(arm * PER_ARM + START_J + pos) % R]; return [c.x, c.y]; }
  const c = board.lane[arm][pos - (R - 1)];
  return [c.x, c.y];
}
