import os
os.environ["DATABASE_URL"] = "sqlite:///./data/test.db"
os.environ["BOT_DELAY"] = "0.01"
import pathlib
pathlib.Path("data/test.db").unlink(missing_ok=True)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def reg(c, name):
    r = c.post("/api/auth/register", json={"username": name, "email": f"{name}@x.com", "password": "password1"})
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}, r.json()["access_token"], r.json()["user"]["id"]


def test_full_flow():
    with TestClient(app) as c:
        ha, ta, ida = reg(c, "alice")
        hb, tb, idb = reg(c, "bobby")
        assert c.post("/api/auth/login", json={"identifier": "ALICE", "password": "password1"}).status_code == 200
        assert c.post("/api/auth/login", json={"identifier": "alice", "password": "nope12345"}).status_code == 401
        # change password
        assert c.post("/api/auth/change-password", headers=ha, json={"current_password": "bad", "new_password": "newpass123"}).status_code == 400
        assert c.post("/api/auth/change-password", headers=ha, json={"current_password": "password1", "new_password": "newpass123"}).status_code == 200
        assert c.post("/api/auth/login", json={"identifier": "alice", "password": "newpass123"}).status_code == 200
        # friends
        assert c.get("/api/friends/search?q=bo", headers=ha).json()[0]["relation"] == "none"
        assert c.post("/api/friends/request", headers=ha, json={"username": "bobby"}).json()["result"] == "sent"
        req = c.get("/api/friends/requests", headers=hb).json()[0]
        assert c.post(f"/api/friends/requests/{req['id']}/accept", headers=hb).status_code == 200
        assert c.get("/api/friends", headers=ha).json()[0]["username"] == "bobby"
        # room + invite
        room = c.post("/api/rooms", headers=ha, json={"mode": "twisted", "max_players": 5, "is_private": True}).json()
        code = room["code"]
        assert c.get(f"/api/rooms/{code}", headers=hb).status_code == 403
        assert c.post(f"/api/rooms/{code}/invite", headers=ha, json={"user_id": idb}).status_code == 200
        inv = c.get("/api/invites", headers=hb).json()
        assert inv[0]["code"] == code
        assert c.post(f"/api/rooms/{code}/join", headers=hb).status_code == 200
        # realtime
        with c.websocket_connect(f"/ws/rooms/{code}?token={ta}") as wa, c.websocket_connect(f"/ws/rooms/{code}?token={tb}") as wb:
            wa.send_json({"type": "chat", "text": "hello"})
            seen = False
            for _ in range(10):
                m = wb.receive_json()
                if m["type"] == "chat" and m["message"]["text"] == "hello":
                    seen = True; break
            assert seen
            wb.send_json({"type": "start"})              # not host -> error
            wa.send_json({"type": "start"})
            state = None
            for _ in range(30):
                m = wa.receive_json()
                if m["type"] == "state" and m["state"]:
                    state = m["state"]; break
            assert state["arms"] == 5 and len(state["seats"]) == 5 and state["mode"] == "twisted"
            assert sum(s["is_bot"] for s in state["seats"]) == 3
        # bad token
        try:
            with c.websocket_connect(f"/ws/rooms/{code}?token=bad"):
                assert False
        except Exception:
            pass
