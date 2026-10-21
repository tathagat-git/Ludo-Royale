import random

from app.services import bot, game_engine as e


def mk(mode="classic", n=4):
    return e.new_game(mode, [{"user_id": i, "name": f"p{i}", "is_bot": False} for i in range(n)])


def test_needs_six_to_leave_yard():
    s = mk()
    e.roll(s, value=3)
    assert s.turn == 1 and s.pieces[0] == [-1] * 4          # no move, turn passes
    e.roll(s, value=6)
    assert s.legal and all(m["to"] == 0 for m in s.legal)


def test_six_gives_extra_turn_and_three_sixes_forfeit():
    s = mk()
    e.roll(s, value=6); e.move(s, 0, "f")
    assert s.turn == 0
    e.roll(s, value=6); e.move(s, 0, "f")
    e.roll(s, value=6)
    assert s.turn == 1 and s.dice is None


def test_capture_and_safe_cell():
    s = mk(n=2)                                   # seats on arm 0 and arm 2
    s.pieces[0][0] = 5
    cell = e.abs_cell(s, 0, 5)
    # place seat 1 piece so that +2 lands on that cell
    target = next(p for p in range(s.ring - 1) if e.abs_cell(s, 1, p) == cell)
    s.pieces[1][0] = target - 2
    s.turn = 1
    e.roll(s, value=2)
    e.move(s, 0, "f")
    assert cell not in e.safe_cells(s)
    assert s.pieces[0][0] == -1 and s.turn == 1           # captured -> extra turn


def test_start_cell_is_safe():
    s = mk(n=2)
    start1 = e.abs_cell(s, 1, 0)
    assert start1 in e.safe_cells(s)
    s.pieces[1][0] = 0
    s.pieces[0][0] = next(p for p in range(s.ring - 1) if e.abs_cell(s, 0, p) == start1) - 1
    e.roll(s, value=1); e.move(s, 0, "f")
    assert s.pieces[1][0] == 0                                  # protected


def test_exact_roll_to_finish():
    s = mk()
    s.pieces[0][0] = s.home - 2
    e.roll(s, value=3)
    assert not any(m["piece"] == 0 for m in s.legal)


def test_twisted_backward_rules():
    s = mk("twisted")
    s.pieces[0] = [0, 3, -1, -1]
    e.roll(s, value=5)
    moves = {(m["piece"], m["dir"], m["to"]) for m in s.legal}
    assert (0, "b", 0) not in {(m["piece"], m["dir"], m["to"]) for m in s.legal if m["piece"] == 0 and m["dir"] == "b"}
    assert (1, "b", 0) in moves                                  # clamps at start point
    assert (0, "f", 5) in moves and (1, "f", 8) in moves
    c = mk("classic"); c.pieces[0] = [0, 3, -1, -1]; e.roll(c, value=5)
    assert all(m["dir"] == "f" for m in c.legal)


def test_win_ends_game():
    s = mk(n=2)
    s.pieces[0] = [s.home, s.home, s.home, s.home - 1]
    e.roll(s, value=1); e.move(s, 3, "f")
    assert s.status == "finished" and s.finished_order[0] == 0


def test_bot_full_games_all_modes_and_sizes():
    for mode in ("classic", "twisted"):
        for n in (2, 3, 4, 5, 6):
            s = mk(mode, n)
            rng = random.Random(n)
            for _ in range(20000):
                if s.status != "playing":
                    break
                if s.dice is None:
                    e.roll(s, rng)
                else:
                    m = bot.choose_move(s); e.move(s, m["piece"], m["dir"])
            assert s.status == "finished", (mode, n)
            assert sorted(s.finished_order) == list(range(n))
