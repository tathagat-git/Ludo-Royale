from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import create_token, get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import ChangePasswordIn, LoginIn, RegisterIn, TokenOut, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    user = auth_service.register(db, body)
    return TokenOut(access_token=create_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, body.identifier, body.password)
    return TokenOut(access_token=create_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password")
def change_password(body: ChangePasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_service.change_password(db, user, body.current_password, body.new_password)
    return {"ok": True}
