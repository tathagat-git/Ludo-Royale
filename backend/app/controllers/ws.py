from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.database import SessionLocal
from app.models.user import User
from app.services import room_service
from app.services.realtime import manager

router = APIRouter()


@router.websocket("/ws/rooms/{code}")
async def room_socket(websocket: WebSocket, code: str, token: str = Query(...)):
    with SessionLocal() as db:
        uid = decode_token(token)
        user = db.get(User, uid) if uid else None
        room = room_service.find(db, code)
        allowed = bool(user and room and room_service.is_member(db, room.id, user.id))
    if not allowed:
        await websocket.close(code=4403)
        return
    await websocket.accept()
    rt = manager.get(code)
    await rt.connect(user, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if isinstance(data, dict):
                await rt.handle(user, data)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await rt.disconnect(user, websocket)
        manager.release_if_idle(code)
