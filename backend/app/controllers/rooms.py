from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.rooms import InviteIn, InviteOut, RoomCreateIn, RoomOut
from app.services import room_service

router = APIRouter(tags=["rooms"])


@router.post("/rooms", response_model=RoomOut, status_code=201)
def create_room(body: RoomCreateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return room_service.view(db, room_service.create(db, user, body))


@router.get("/rooms/public", response_model=list[RoomOut])
def public_rooms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return room_service.list_public(db)


@router.get("/rooms/{code}", response_model=RoomOut)
def get_room(code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room = room_service.get_or_404(db, code)
    if room.is_private and not room_service.is_member(db, room.id, user.id):
        raise AppError("Private room - join with the code", 403)
    return room_service.view(db, room)


@router.post("/rooms/{code}/join", response_model=RoomOut)
def join_room(code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return room_service.view(db, room_service.join(db, user, code))


@router.post("/rooms/{code}/leave")
def leave_room(code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room_service.leave(db, user, code)
    return {"ok": True}


@router.post("/rooms/{code}/invite")
def invite(code: str, body: InviteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room_service.invite(db, user, code, body.user_id)
    return {"ok": True}


@router.get("/invites", response_model=list[InviteOut])
def my_invites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return room_service.my_invites(db, user)


@router.post("/invites/{invite_id}/decline")
def decline_invite(invite_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room_service.decline_invite(db, user, invite_id)
    return {"ok": True}
