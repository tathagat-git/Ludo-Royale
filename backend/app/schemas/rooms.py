from typing import Literal

from pydantic import BaseModel, Field


class RoomCreateIn(BaseModel):
    mode: Literal["classic", "twisted"] = "classic"
    max_players: int = Field(default=4, ge=2, le=6)
    is_private: bool = True
    fill_with_bots: bool = True


class MemberOut(BaseModel):
    user_id: int
    username: str
    seat: int


class RoomOut(BaseModel):
    code: str
    host_id: int
    mode: str
    max_players: int
    is_private: bool
    fill_with_bots: bool
    status: str
    members: list[MemberOut]


class InviteIn(BaseModel):
    user_id: int


class InviteOut(BaseModel):
    id: int
    code: str
    mode: str
    from_username: str
