# 🎲 Ludo Royale

Full-stack Ludo: **FastAPI + SQLite** backend, **React (Vite)** frontend, real-time play over WebSockets.

* **Classic** – traditional rules (6 to leave yard, exact roll to finish, captures, safe cells, 6 = extra turn, three 6s = turn lost).
* **Twisted** – every piece can move forward *or* backward by the dice value, but never behind its own start cell.
* 2–6 players (4-arm cross board for 2–4, 5-arm and 6-arm boards for 5/6), bots fill empty seats.
* Accounts (JWT), change password, friends, friend requests, invite friends to a private party, room chat.

## Architecture (MVC)
| Layer | Folder |
|---|---|
| Model (SQLAlchemy tables) | `backend/app/models` |
| Controller (FastAPI routers + WebSocket) | `backend/app/controllers` |
| Service / business logic (game engine, bots, realtime) | `backend/app/services` |
| View (JSON schemas + React UI) | `backend/app/schemas`, `frontend/src` |

## Run locally
```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload            # http://localhost:8000/docs

# frontend (new terminal)
cd frontend && npm install && npm run dev  # http://localhost:5173 (proxies /api and /ws)

# tests
cd backend && pytest
```

## Deploy on Render
1. Push this folder to GitHub.
2. Render → New → **Blueprint** → select the repo (uses `render.yaml`).
3. Done. `SECRET_KEY` is generated automatically.

Important notes
* **Run exactly one worker** (`--workers 1`): live games and sockets are kept in memory. Game state is also saved to SQLite after each move, so games resume after a restart.
* SQLite needs a **persistent disk** (paid plan). On the free plan the database is wiped on each deploy.
* To scale beyond one instance, move room state to Redis pub/sub and SQLite to Postgres (only `DATABASE_URL` and `realtime.py` change).

## Env vars
`SECRET_KEY`, `DATABASE_URL`, `TURN_SECONDS` (default 30, auto-play on timeout), `BOT_DELAY`, `CORS_ORIGINS`.
