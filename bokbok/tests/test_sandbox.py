"""공개 테스트 모드: 브라우저(쿠키)마다 체험 공간이 분리되는지"""

import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app


@pytest.fixture
def multi(tmp_path, monkeypatch):
    monkeypatch.setenv("BOKBOK_MULTI", "1")
    monkeypatch.setenv("BOKBOK_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("BOKBOK_TODAY", "2026-11-14")
    monkeypatch.delenv("BOKBOK_LLM_MODEL", raising=False)
    return tmp_path / "sessions"


def test_each_browser_gets_its_own_sandbox(multi):
    a, b = TestClient(app), TestClient(app)
    a.get("/")
    b.get("/")
    assert a.cookies.get(store.SESSION_COOKIE) != b.cookies.get(store.SESSION_COOKIE)

    a.post("/student/welcome", data={"family": "가족A"})
    a.post("/student/record", data={"emotion": "sad", "note": "A팀 테스트 문장입니다"})
    a.post("/api/chat", data={"text": "사라지고싶어"})

    # A의 기록과 알림은 A에게만 보임
    assert "A팀 테스트 문장입니다" in a.get("/student/report").text
    assert "하늘 학생" in a.get("/teacher").text
    assert b.get("/student", follow_redirects=False).headers["location"] == "/student/welcome"
    b.post("/student/welcome", data={"action": "skip"})
    assert "A팀 테스트 문장입니다" not in b.get("/student/report").text
    assert "하늘 학생" not in b.get("/teacher").text
    assert len([d for d in multi.iterdir() if d.is_dir()]) == 2


def test_reset_only_clears_own_sandbox(multi):
    a, b = TestClient(app), TestClient(app)
    for c in (a, b):
        c.post("/student/welcome", data={"family": "가족"})
    a.post("/reset", data={"next": "/"})
    assert a.get("/student", follow_redirects=False).headers["location"] == "/student/welcome"
    assert b.get("/student", follow_redirects=False).headers["location"] == "/student/record"


def test_uploads_are_private_to_sandbox(multi):
    a, b = TestClient(app), TestClient(app)
    a.post("/teacher/shop/items", data={"name": "칭찬 스티커", "price": "10", "on_sale": "1"},
           files={"image": ("s.png", b"\x89PNG\r\n\x1a\n0000", "image/png")})
    store.use_session(a.cookies.get(store.SESSION_COOKIE))
    image = [i for i in store.load()["items"] if i["name"] == "칭찬 스티커"][0]["image"]
    store.use_session(None)
    assert a.get(f"/uploads/{image}").status_code == 200
    assert b.get(f"/uploads/{image}").status_code == 404


def test_forged_cookie_is_replaced(multi):
    res = TestClient(app).get("/", headers={"cookie": f"{store.SESSION_COOKIE}=../../etc"})
    sid = res.cookies.get(store.SESSION_COOKIE)
    assert store.valid_sid(sid)
    assert not (multi.parent / "etc").exists()

