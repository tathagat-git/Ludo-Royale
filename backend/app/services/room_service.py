import json
import secrets
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.room import ChatMessage, Room, RoomInvite, RoomMember
from app.models.user import User
from app.schemas.rooms import RoomCreateIn
from app.services import friend_service

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _new_code(db: Session) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(_ALPHABET) for _ in range(6))
        if not db.scalar(select(Room.id).where(Room.code == code)):
            return code
    raise AppError("Could not allocate room code", 500)


def find(db: Session, code: str) -> Optional[Room]:
    return db.scalar(select(Room).where(Room.code == code.strip().upper()))


def get_or_404(db: Session, code: str) -> Room:
    room = find(db, code)
    if not room:
        raise AppError("Room not found", 404)
    return room


def members(db: Session, room: Room) -> list[RoomMember]:
    return list(db.scalars(select(RoomMember).where(RoomMember.room_id == room.id).order_by(RoomMember.seat)).unique().all())


def is_member(db: Session, room_id: int, user_id: int) -> bool:
    return bool(db.scalar(select(RoomMember.id).where(RoomMember.room_id == room_id, RoomMember.user_id == user_id)))


def view(db: Session, room: Room) -> dict:
    return {
        "code": room.code, "host_id": room.host_id, "mode": room.mode, "max_players": room.max_players,
        "is_private": room.is_private, "fill_with_bots": room.fill_with_bots, "status": room.status,
        "members": [{"user_id": m.user_id, "username": m.user.username, "seat": m.seat} for m in members(db, room)],
    }


def create(db: Session, host: User, data: RoomCreateIn) -> Room:
    room = Room(code=_new_code(db), host_id=host.id, mode=data.mode, max_players=data.max_players,
                is_private=data.is_private, fill_with_bots=data.fill_with_bots)
    db.add(room)
    db.flush()
    db.add(RoomMember(room_id=room.id, user_id=host.id, seat=0))
    db.commit()
    return room


def join(db: Session, user: User, code: str) -> Room:
    room = get_or_404(db, code)
    if is_member(db, room.id, user.id):
        return room
    if room.status != "lobby":
        raise AppError("Game already started", 409)
    taken = {m.seat for m in members(db, room)}
    free = [s for s in range(room.max_players) if s not in taken]
    if not free:
        raise AppError("Room is full", 409)
    db.add(RoomMember(room_id=room.id, user_id=user.id, seat=free[0]))
    for inv in db.scalars(select(RoomInvite).where(RoomInvite.room_id == room.id, RoomInvite.to_user_id == user.id,
                                                  RoomInvite.status == "pending")).unique():
        inv.status = "accepted"
    db.commit()
    return room


def leave(db: Session, user: User, code: str) -> None:
    room = get_or_404(db, code)
    if room.status != "lobby":
        raise AppError("Game already started", 409)
    mem = db.scalar(select(RoomMember).where(RoomMember.room_id == room.id, RoomMember.user_id == user.id))
    if not mem:
        return
    db.delete(mem)
    db.flush()
    rest = members(db, room)
    if not rest:
        db.delete(room)
    elif room.host_id == user.id:
        room.host_id = rest[0].user_id
    db.commit()


def list_public(db: Session) -> list[dict]:
    rooms = db.scalars(select(Room).where(Room.is_private.is_(False), Room.status == "lobby")
                       .order_by(Room.id.desc()).limit(20)).all()
    return [view(db, r) for r in rooms]


def build_players(db: Session, room: Room) -> list[dict]:
    by_seat = {m.seat: m for m in members(db, room)}
    players = []
    for seat in range(room.max_players):
        if seat in by_seat:
            players.append({"user_id": by_seat[seat].user_id, "name": by_seat[seat].user.username, "is_bot": False})
        elif room.fill_with_bots:
            players.append({"user_id": None, "name": f"Bot {seat + 1}", "is_bot": True})
    return players


def save_state(db: Session, room: Room, state: dict, status: str) -> None:
    room.state_json = json.dumps(state)
    room.status = status
    db.add(room)
    db.commit()


def add_chat(db: Session, room: Room, user: User, text: str) -> dict:
    msg = ChatMessage(room_id=room.id, user_id=user.id, text=text)
    db.add(msg)
    db.commit()
    return chat_view(msg)


def chat_view(m: ChatMessage) -> dict:
    return {"id": m.id, "user_id": m.user_id, "username": m.user.username, "text": m.text,
            "at": m.created_at.isoformat() if m.created_at else None}


def recent_chat(db: Session, room: Room, limit: int = 50) -> list[dict]:
    rows = db.scalars(select(ChatMessage).where(ChatMessage.room_id == room.id)
                      .order_by(ChatMessage.id.desc()).limit(limit)).unique().all()
    return [chat_view(m) for m in reversed(rows)]


# ---- invites ----
def invite(db: Session, me: User, code: str, friend_id: int) -> None:
    room = get_or_404(db, code)
    if not is_member(db, room.id, me.id):
        raise AppError("Join the room first", 403)
    if room.status != "lobby":
        raise AppError("Game already started", 409)
    if not friend_service.are_friends(db, me.id, friend_id):
        raise AppError("You can only invite friends", 403)
    if is_member(db, room.id, friend_id):
        raise AppError("Already in the room", 409)
    pending = db.scalar(select(RoomInvite).where(RoomInvite.room_id == room.id, RoomInvite.to_user_id == friend_id,
                                                 RoomInvite.status == "pending"))
    if not pending:
        db.add(RoomInvite(room_id=room.id, from_user_id=me.id, to_user_id=friend_id))
        db.commit()


def my_invites(db: Session, me: User) -> list[dict]:
    rows = db.scalars(select(RoomInvite).where(RoomInvite.to_user_id == me.id, RoomInvite.status == "pending")
                      .order_by(RoomInvite.id.desc())).unique().all()
    return [{"id": i.id, "code": i.room.code, "mode": i.room.mode, "from_username": i.from_user.username}
            for i in rows if i.room.status == "lobby"]


def decline_invite(db: Session, me: User, invite_id: int) -> None:
    inv = db.get(RoomInvite, invite_id)
    if not inv or inv.to_user_id != me.id:
        raise AppError("Invite not found", 404)
    inv.status = "declined"
    db.commit()
