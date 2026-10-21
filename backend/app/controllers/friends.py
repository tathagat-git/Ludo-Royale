from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.friends import FriendOut, FriendRequestIn, FriendRequestOut, SearchOut
from app.services import friend_service

router = APIRouter(prefix="/friends", tags=["friends"])


@router.get("", response_model=list[FriendOut])
def friends(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [FriendOut(id=u.id, username=u.username) for u in friend_service.list_friends(db, user)]


@router.get("/requests", response_model=list[FriendRequestOut])
def requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [FriendRequestOut(id=f.id, from_user=FriendOut(id=f.requester.id, username=f.requester.username))
            for f in friend_service.incoming(db, user)]


@router.get("/search", response_model=list[SearchOut])
def search(q: str = "", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return friend_service.search(db, user, q)


@router.post("/request")
def send_request(body: FriendRequestIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"result": friend_service.send_request(db, user, body.username)}


@router.post("/requests/{request_id}/accept")
def accept(request_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    friend_service.respond(db, user, request_id, True)
    return {"ok": True}


@router.post("/requests/{request_id}/decline")
def decline(request_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    friend_service.respond(db, user, request_id, False)
    return {"ok": True}


@router.delete("/{user_id}")
def remove(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    friend_service.remove(db, user, user_id)
    return {"ok": True}
