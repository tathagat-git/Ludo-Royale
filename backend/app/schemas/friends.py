from pydantic import BaseModel, Field


class FriendOut(BaseModel):
    id: int
    username: str


class FriendRequestIn(BaseModel):
    username: str = Field(min_length=3, max_length=24)


class FriendRequestOut(BaseModel):
    id: int
    from_user: FriendOut


class SearchOut(BaseModel):
    id: int
    username: str
    relation: str   # none | friends | sent | received
