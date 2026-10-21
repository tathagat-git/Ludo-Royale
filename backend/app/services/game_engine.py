"""Pure Ludo rules (classic + twisted). No FastAPI / DB imports, so it is easy to unit-test.

Board model
-----------
* The shared ring has `arms * 13` cells. Arm k owns ring cells k*13 .. k*13+12.
* A piece position is relative to its owner's start cell:
    -1              -> in the yard
    0 .. ring-2     -> on the shared ring (abs cell = arm*13 + START_J + pos)
    ring-1 .. ring+3-> private home lane (5 cells)
    ring+4          -> HOME (finished)
* Twisted mode: a piece may also move BACKWARD, but never below pos 0 (its start cell).
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from typing import Optional

CELLS_PER_ARM = 13
START_J = 8          # start cell = 9th cell of the owner's arm
STAR_OFFSET = 8      # star (safe) cell is 8 steps after every start cell
PIECES = 4
COLORS = ["red", "green", "yellow", "blue", "purple", "orange"]
ARMS_FOR_PLAYERS = {2: [0, 2], 3: [0, 1, 2], 4: [0, 1, 2, 3], 5: [0, 1, 2, 3, 4], 6: [0, 1, 2, 3, 4, 5]}
MODES = ("classic", "twisted")


class RuleError(Exception):
    pass


@dataclass
class Seat:
    seat: int
    arm: int
    color: str
    user_id: Optional[int]
    name: str
    is_bot: bool


@dataclass
class GameState:
    mode: str
    arms: int
    seats: list
    pieces: list                       # pieces[seat][piece] -> pos
    turn: int = 0
    dice: Optional[int] = None
    legal: list = field(default_factory=list)
    sixes: int = 0
    finished_order: list = field(default_factory=list)
    status: str = "playing"            # playing | finished
    last_event: str = "Game started"
    last_roll: Optional[dict] = None
    last_move: Optional[dict] = None
    move_no: int = 0

    @property
    def ring(self) -> int:
        return self.arms * CELLS_PER_ARM

    @property
    def home(self) -> int:
        return self.ring + 4

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "GameState":
        d = dict(d)
        d["seats"] = [Seat(**s) for s in d["seats"]]
        return cls(**d)


def new_game(mode: str, players: list[dict]) -> GameState:
    if mode not in MODES:
        raise RuleError("Unknown mode")
    n = len(players)
    if n not in ARMS_FOR_PLAYERS:
        raise RuleError("2 to 6 players required")
    arm_ids = ARMS_FOR_PLAYERS[n]
    seats = [
        Seat(i, arm_ids[i], COLORS[arm_ids[i]], p.get("user_id"), p["name"], bool(p.get("is_bot")))
        for i, p in enumerate(players)
    ]
    return GameState(mode=mode, arms=4 if n <= 4 else n, seats=seats, pieces=[[-1] * PIECES for _ in seats])


# ---------------------------------------------------------------- helpers
def abs_cell(s: GameState, seat: int, pos: int) -> Optional[int]:
    if pos < 0 or pos > s.ring - 2:
        return None
    return (s.seats[seat].arm * CELLS_PER_ARM + START_J + pos) % s.ring


def safe_cells(s: GameState) -> set:
    out = set()
    for arm in range(s.arms):
        start = arm * CELLS_PER_ARM + START_J
        out.add(start % s.ring)
        out.add((start + STAR_OFFSET) % s.ring)
    return out


def legal_moves(s: GameState, seat: int, dice: int) -> list:
    moves = []
    for i, pos in enumerate(s.pieces[seat]):
        if pos == s.home:
            continue
        if pos == -1:
            if dice == 6:
                moves.append({"piece": i, "dir": "f", "to": 0})
            continue
        if pos + dice <= s.home:                       # exact roll needed to finish
            moves.append({"piece": i, "dir": "f", "to": pos + dice})
        if s.mode == "twisted" and pos > 0:            # cannot go back from the start cell
            moves.append({"piece": i, "dir": "b", "to": max(0, pos - dice)})
    return moves


def victims_at(s: GameState, seat: int, cell: int) -> list:
    out = []
    for o in range(len(s.seats)):
        if o == seat:
            continue
        for j, p in enumerate(s.pieces[o]):
            if abs_cell(s, o, p) == cell:
                out.append((o, j))
    return out


def _advance(s: GameState) -> None:
    n = len(s.seats)
    for step in range(1, n + 1):
        j = (s.turn + step) % n
        if j not in s.finished_order:
            s.turn = j
            break
    s.dice, s.legal, s.sixes = None, [], 0


# ---------------------------------------------------------------- actions
def roll(s: GameState, rng: random.Random = random, value: Optional[int] = None) -> None:
    if s.status != "playing":
        raise RuleError("Game is over")
    if s.dice is not None:
        raise RuleError("Dice already rolled")
    d = value or rng.randint(1, 6)
    name = s.seats[s.turn].name
    s.dice = d
    s.last_roll = {"seat": s.turn, "value": d}
    s.sixes = s.sixes + 1 if d == 6 else 0
    if s.sixes >= 3:
        s.last_event = f"{name} rolled three 6s - turn lost"
        _advance(s)
        return
    s.legal = legal_moves(s, s.turn, d)
    if not s.legal:
        s.last_event = f"{name} rolled {d} - no move possible"
        _advance(s)
    else:
        s.last_event = f"{name} rolled {d}"


def move(s: GameState, piece: int, direction: str) -> None:
    if s.status != "playing" or s.dice is None:
        raise RuleError("Roll the dice first")
    m = next((m for m in s.legal if m["piece"] == piece and m["dir"] == direction), None)
    if not m:
        raise RuleError("Illegal move")
    seat = s.turn
    name = s.seats[seat].name
    old, new = s.pieces[seat][piece], m["to"]
    s.pieces[seat][piece] = new

    captured = 0
    cell = abs_cell(s, seat, new)
    if cell is not None and cell not in safe_cells(s):
        for o, j in victims_at(s, seat, cell):
            s.pieces[o][j] = -1
            captured += 1

    reached_home = new == s.home
    extra = s.dice == 6 or captured > 0 or reached_home
    s.move_no += 1
    s.last_move = {"seat": seat, "piece": piece, "from": old, "to": new, "captured": captured}
    s.last_event = f"{name} moved {'back' if direction == 'b' else 'forward'}"
    if captured:
        s.last_event += f" and captured {captured} piece{'s' if captured > 1 else ''}!"
    elif reached_home:
        s.last_event += " and reached home!"

    if all(p == s.home for p in s.pieces[seat]):
        s.finished_order.append(seat)
        s.last_event = f"{name} finished #{len(s.finished_order)}!"
        extra = False

    s.dice, s.legal = None, []
    remaining = [i for i in range(len(s.seats)) if i not in s.finished_order]
    if len(remaining) <= 1:
        s.finished_order.extend(remaining)
        s.status = "finished"
        return
    if not extra:
        _advance(s)
