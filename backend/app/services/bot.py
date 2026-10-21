"""Heuristic bot used for empty seats and for auto-play of idle / disconnected humans."""
from app.services.game_engine import GameState, abs_cell, safe_cells, victims_at


def _in_danger(s: GameState, seat: int, pos: int) -> bool:
    cell = abs_cell(s, seat, pos)
    if cell is None or cell in safe_cells(s):
        return False
    R = s.ring
    for o in range(len(s.seats)):
        if o == seat:
            continue
        for p in s.pieces[o]:
            oc = abs_cell(s, o, p)
            if oc is None:
                continue
            if 1 <= (cell - oc) % R <= 6:                       # hunter behind us
                return True
            if s.mode == "twisted" and p > 0 and 1 <= (oc - cell) % R <= 6:   # hunter can step back
                return True
    return False


def _score(s: GameState, seat: int, m: dict) -> float:
    pos, to = s.pieces[seat][m["piece"]], m["to"]
    cell = abs_cell(s, seat, to)
    score = 0.0
    if m["dir"] == "b":
        score -= 25
    else:
        score += (to - pos) * 0.5
    if to == s.home:
        score += 100
    if cell is not None and cell not in safe_cells(s):
        v = len(victims_at(s, seat, cell))
        if v:
            score += 80 + 5 * v
    if pos == -1:
        score += 45
    if cell is not None and cell in safe_cells(s):
        score += 15
    if s.ring - 1 <= to < s.home:
        score += 12
    before, after = _in_danger(s, seat, pos), _in_danger(s, seat, to)
    if before and not after:
        score += 18
    if after and not before:
        score -= 18
    return score


def choose_move(s: GameState) -> dict:
    return max(s.legal, key=lambda m: _score(s, s.turn, m))
