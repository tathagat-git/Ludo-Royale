from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.friendship import Friendship
from app.models.user import User


def _between(db: Session, a: int, b: int):
    return db.scalar(select(Friendship).where(or_(
        and_(Friendship.requester_id == a, Friendship.addressee_id == b),
        and_(Friendship.requester_id == b, Friendship.addressee_id == a))))


def are_friends(db: Session, a: int, b: int) -> bool:
    f = _between(db, a, b)
    return bool(f and f.status == "accepted")


def list_friends(db: Session, me: User) -> list[User]:
    rows = db.scalars(select(Friendship).where(
        Friendship.status == "accepted",
        or_(Friendship.requester_id == me.id, Friendship.addressee_id == me.id))).unique().all()
    friends = [r.addressee if r.requester_id == me.id else r.requester for r in rows]
    return sorted(friends, key=lambda u: u.username)


def incoming(db: Session, me: User) -> list[Friendship]:
    return list(db.scalars(select(Friendship).where(
        Friendship.addressee_id == me.id, Friendship.status == "pending")).unique().all())


def search(db: Session, me: User, q: str) -> list[dict]:
    q = q.strip().lower()
    if len(q) < 2:
        return []
    users = db.scalars(select(User).where(User.username.like(f"%{q}%"), User.id != me.id).limit(10)).all()
    out = []
    for u in users:
        f = _between(db, me.id, u.id)
        rel = "none"
        if f:
            rel = "friends" if f.status == "accepted" else ("sent" if f.requester_id == me.id else "received")
        out.append({"id": u.id, "username": u.username, "relation": rel})
    return out


def send_request(db: Session, me: User, username: str) -> str:
    target = db.scalar(select(User).where(User.username == username.strip().lower()))
    if not target:
        raise AppError("User not found", 404)
    if target.id == me.id:
        raise AppError("You cannot add yourself", 400)
    f = _between(db, me.id, target.id)
    if f:
        if f.status == "accepted":
            raise AppError("Already friends", 409)
        if f.requester_id == me.id:
            raise AppError("Request already sent", 409)
        f.status = "accepted"                       # they already asked us -> auto accept
        db.commit()
        return "accepted"
    db.add(Friendship(requester_id=me.id, addressee_id=target.id))
    db.commit()
    return "sent"


def respond(db: Session, me: User, request_id: int, accept: bool) -> None:
    f = db.get(Friendship, request_id)
    if not f or f.addressee_id != me.id or f.status != "pending":
        raise AppError("Request not found", 404)
    if accept:
        f.status = "accepted"
    else:
        db.delete(f)
    db.commit()


def remove(db: Session, me: User, user_id: int) -> None:
    f = _between(db, me.id, user_id)
    if not f:
        raise AppError("Not friends", 404)
    db.delete(f)
    db.commit()
