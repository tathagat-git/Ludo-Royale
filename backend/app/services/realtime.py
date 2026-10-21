"""Real-time room runtime: websocket connections, authoritative game loop, bots, chat."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional

from fastapi import WebSocket

from app.config import settings
from app.database import SessionLocal
from app.models.user import User
from app.services import bot, game_engine as engine, room_service

log = logging.getLogger("ludo.realtime")
CHAT_COOLDOWN = 0.6


class RoomRuntime:
    def __init__(self, code: str):
        self.code = code
        self.sockets: dict[int, set[WebSocket]] = {}
        self.state: Optional[engine.GameState] = None
        self.task: Optional[asyncio.Task] = None
        self.deadline: Optional[float] = None
        self._last_chat: dict[int, float] = {}
        with SessionLocal() as db:
            room = room_service.find(db, code)
            if room and room.state_json:
                self.state = engine.GameState.from_dict(json.loads(room.state_json))

    # ------------------------------------------------------------ plumbing
    def online_ids(self) -> set:
        return {u for u, s in self.sockets.items() if s}

    async def _send(self, ws: WebSocket, payload: dict) -> None:
        try:
            await ws.send_json(payload)
        except Exception:
            pass

    async def broadcast(self, payload: dict) -> None:
        for conns in list(self.sockets.values()):
            for ws in list(conns):
                await self._send(ws, payload)

    def _state_payload(self) -> dict:
        return {"type": "state", "state": self.state.to_dict() if self.state else None,
                "deadline": self.deadline, "server_time": time.time()}

    async def broadcast_room(self) -> None:
        with SessionLocal() as db:
            room = room_service.find(db, self.code)
            if not room:
                return
            data = room_service.view(db, room)
        data["online"] = sorted(self.online_ids())
        await self.broadcast({"type": "room", "room": data})

    # ------------------------------------------------------------ lifecycle
    async def connect(self, user: User, ws: WebSocket) -> None:
        self.sockets.setdefault(user.id, set()).add(ws)
        with SessionLocal() as db:
            room = room_service.find(db, self.code)
            history = room_service.recent_chat(db, room)
        await self._send(ws, {"type": "history", "messages": history})
        await self.broadcast_room()
        await self._send(ws, self._state_payload())
        if self.state and self.state.status == "playing" and (not self.task or self.task.done()):
            self.schedule()

    async def disconnect(self, user: User, ws: WebSocket) -> None:
        self.sockets.get(user.id, set()).discard(ws)
        await self.broadcast_room()

    def idle(self) -> bool:
        return not self.online_ids() and not (self.state and self.state.status == "playing")

    # ------------------------------------------------------------ client messages
    async def handle(self, user: User, data: dict) -> None:
        kind = data.get("type")
        try:
            if kind == "chat":
                await self._chat(user, str(data.get("text", "")))
            elif kind == "start":
                await self._start(user)
            elif kind == "roll":
                self._require_turn(user)
                engine.roll(self.state)
                self._changed()
            elif kind == "move":
                self._require_turn(user)
                engine.move(self.state, int(data.get("piece", -1)), str(data.get("dir", "f")))
                self._changed()
        except (engine.RuleError, ValueError) as e:
            for ws in self.sockets.get(user.id, set()):
                await self._send(ws, {"type": "error", "message": str(e)})

    def _require_turn(self, user: User) -> None:
        s = self.state
        if not s or s.status != "playing":
            raise engine.RuleError("Game is not running")
        if s.seats[s.turn].user_id != user.id:
            raise engine.RuleError("It is not your turn")

    async def _chat(self, user: User, text: str) -> None:
        text = " ".join(text.split())[:300]
        now = time.monotonic()
        if not text or now - self._last_chat.get(user.id, 0) < CHAT_COOLDOWN:
            return
        self._last_chat[user.id] = now
        with SessionLocal() as db:
            room = room_service.find(db, self.code)
            msg = room_service.add_chat(db, room, user, text)
        await self.broadcast({"type": "chat", "message": msg})

    async def _start(self, user: User) -> None:
        with SessionLocal() as db:
            room = room_service.find(db, self.code)
            if room.host_id != user.id:
                raise engine.RuleError("Only the host can start")
            if room.status != "lobby":
                raise engine.RuleError("Game already started")
            players = room_service.build_players(db, room)
            if len(players) < 2:
                raise engine.RuleError("Need at least 2 players (or enable bots)")
            self.state = engine.new_game(room.mode, players)
            room_service.save_state(db, room, self.state.to_dict(), "playing")
        await self.broadcast_room()
        self._changed()

    # ------------------------------------------------------------ game loop
    def _persist(self) -> None:
        if not self.state:
            return
        with SessionLocal() as db:
            room = room_service.find(db, self.code)
            if room:
                room_service.save_state(db, room, self.state.to_dict(), self.state.status)

    def _changed(self) -> None:
        self._persist()
        self.schedule()

    def schedule(self) -> None:
        if self.task and not self.task.done():
            self.task.cancel()
        self.task = asyncio.create_task(self._drive())

    def _plan_delay(self) -> float:
        s = self.state
        seat = s.seats[s.turn]
        if seat.is_bot:
            self.deadline = None
            return settings.BOT_DELAY
        if seat.user_id not in self.online_ids():
            self.deadline = None
            return 2.0
        self.deadline = time.time() + settings.TURN_SECONDS
        return settings.TURN_SECONDS

    async def _drive(self) -> None:
        try:
            while self.state and self.state.status == "playing":
                delay = self._plan_delay()
                await self.broadcast(self._state_payload())
                await asyncio.sleep(delay)
                s = self.state
                if s.dice is None:
                    engine.roll(s)
                else:
                    m = bot.choose_move(s)
                    engine.move(s, m["piece"], m["dir"])
                self._persist()
            self.deadline = None
            await self.broadcast(self._state_payload())
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("game loop crashed for room %s", self.code)


class RuntimeManager:
    def __init__(self):
        self.rooms: dict[str, RoomRuntime] = {}

    def get(self, code: str) -> RoomRuntime:
        code = code.upper()
        if code not in self.rooms:
            self.rooms[code] = RoomRuntime(code)
        return self.rooms[code]

    def release_if_idle(self, code: str) -> None:
        rt = self.rooms.get(code.upper())
        if rt and rt.idle():
            if rt.task and not rt.task.done():
                rt.task.cancel()
            self.rooms.pop(code.upper(), None)


manager = RuntimeManager()
