"""처음 접속할 때의 약속(동의) 화면과, 약속하지 않은 학생의 복복이 대화 잠금"""

import pytest
from fastapi.testclient import TestClient

from app import data, ledger, store
from app.main import app

pytestmark = pytest.mark.first_visit
TODAY = "2026-11-14"
ALL = {"basic": ["1", "2", "3"], "chat": ["1", "2"]}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BOKBOK_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("BOKBOK_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.setenv("BOKBOK_TODAY", TODAY)
    monkeypatch.delenv("BOKBOK_LLM_MODEL", raising=False)
    return TestClient(app)


def test_emotion_chat_button_requires_chat_agreement(client):
    client.post("/student/promise", data={"basic": ALL["basic"]})
    client.post("/student/welcome", data={"action": "skip"})
    client.post("/student/record", data={"emotion": "sad", "intensity": "4"})

    blocked = client.post("/student/chat/today-emotion", follow_redirects=False)
    assert blocked.status_code == 303
    promise = client.get(blocked.headers["location"])
    assert promise.url.path == "/student/promise"
    assert 'name="today_emotion"' in promise.text

    saved = client.post("/student/promise", data={**ALL, "today_emotion": "1"})
    assert "오늘 감정으로 이야기하기" in saved.text
    assert "‘슬픔 · 많이’" not in client.get("/student/chat").text
    assert "‘슬픔 · 많이’" in client.post("/student/chat/today-emotion").text


def test_first_visit_shows_promise_before_basic_info(client):
    assert client.get("/student", follow_redirects=False).headers["location"] == "/student/welcome"
    assert client.get("/student/welcome", follow_redirects=False).headers["location"] == "/student/promise"
    page = client.get("/student").text  # 따라가면 약속 화면
    for text in data.CHATBOT["promise"]["basic"] + data.CHATBOT["promise"]["chat"]:
        assert text.replace("‘", "&#8216;").replace("’", "&#8217;") in page or text in page
    assert page.count('name="basic"') == 3 and page.count('name="chat"') == 2
    assert page.count("required") >= 3  # 감정 기록 세 가지는 꼭 확인

    client.post("/student/promise", data=ALL)
    assert store.load()["consent"]["basic"] is True and store.load()["consent"]["chat"] is True
    assert "기본 정보" in client.get("/student/welcome").text  # 약속 다음에 기본 정보
    client.post("/student/welcome", data={"action": "skip"})
    assert client.get("/student", follow_redirects=False).headers["location"] == "/student/record"


def test_basic_promise_is_required(client):
    res = client.post("/student/promise", data={"basic": ["1", "2"], "chat": ["1", "2"]}, follow_redirects=False)
    assert "need_basic" in res.headers["location"]
    assert store.load().get("consent") is None


def test_without_chat_promise_chat_is_locked_but_records_work(client):
    client.post("/student/promise", data={"basic": ["1", "2", "3"], "chat": ["1"]})  # 대화 약속은 둘 다 골라야 함
    client.post("/student/welcome", data={"action": "skip"})
    assert store.load()["consent"] == {"basic": True, "chat": False, "date": TODAY, "time": store.load()["consent"]["time"]}

    res = client.get("/student/chat", follow_redirects=False)
    assert res.headers["location"] == "/student/promise?locked=1"
    assert "두 가지를 약속해야 해요" in client.get("/student/chat").text
    assert client.post("/api/chat", data={"text": "안녕"}).status_code == 403
    client.post("/student/chat", data={"text": "안녕"})
    assert store.load()["chats"] == [m for m in store.load()["chats"] if m["date"] != TODAY]  # 오늘 대화가 생기지 않음
    assert not any(e["kind"] == "chat" for e in ledger.entries())

    # 감정 기록과 상점은 그대로 쓸 수 있음
    client.post("/student/record", data={"emotion": "calm", "intensity": "3"})
    assert store.load()["my_records"][0]["emotion"] == "calm"
    assert client.get("/student/shop").status_code == 200


def test_student_can_change_the_chat_promise_later(client):
    client.post("/student/promise", data={"basic": ["1", "2", "3"]})
    client.post("/student/welcome", data={"action": "skip"})
    page = client.get("/student/promise").text
    assert "약속 저장하기" in page
    client.post("/student/promise", data=ALL)
    assert client.get("/student/chat").status_code == 200
    assert "약속 다시 보기" in client.get("/student/chat").text
    assert client.post("/api/chat", data={"text": "안녕"}).status_code == 200


def test_promise_is_kept_in_the_ledger(client):
    client.post("/student/promise", data={"basic": ["1", "2", "3"]})
    client.post("/student/promise", data=ALL)
    kept = [e["payload"] for e in ledger.entries() if e["kind"] == "consent"]
    assert kept == [{"basic": True, "chat": False}, {"basic": True, "chat": True}]  # 바꾼 이력까지 남음
    assert ledger.verify(store.load()["ledger_head"])["ok"]


def test_existing_student_without_promise_is_asked_once(client):
    """약속 화면이 생기기 전부터 쓰던 학생(기본 정보는 있고 약속은 없음)도 한 번은 약속 화면을 거침"""
    with store.editing() as state:
        state["profile_skipped"] = True
    assert client.get("/student", follow_redirects=False).headers["location"] == "/student/promise"
    client.post("/student/promise", data=ALL)
    assert client.get("/student", follow_redirects=False).headers["location"] == "/student/record"
