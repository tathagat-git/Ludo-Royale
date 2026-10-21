from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import RegisterIn


def register(db: Session, data: RegisterIn) -> User:
    username, email = data.username.lower(), data.email.lower()
    exists = db.scalar(select(User).where(or_(User.username == username, User.email == email)))
    if exists:
        raise AppError("Username or email already in use", 409)
    user = User(username=username, email=email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, identifier: str, password: str) -> User:
    ident = identifier.strip().lower()
    user = db.scalar(select(User).where(or_(User.username == ident, User.email == ident)))
    if not user or not verify_password(password, user.password_hash):
        raise AppError("Invalid username or password", 401)
    return user


def change_password(db: Session, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        raise AppError("Current password is incorrect", 400)
    if current == new:
        raise AppError("New password must be different", 400)
    user.password_hash = hash_password(new)
    db.add(user)
    db.commit()
