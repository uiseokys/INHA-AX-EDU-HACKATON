"""날짜별 대화 기록: 하루 요약 + 그날 대화 원문 (학생 본인만 봄)"""

import pytest
from fastapi.testclient import TestClient

from app import chatbot, data, llm, store
from app.main import app

TODAY = "2026-11-14"
YESTERDAY = "2026-11-13"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BOKBOK_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("BOKBOK_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.setenv("BOKBOK_TODAY", TODAY)
    monkeypatch.delenv("BOKBOK_LLM_MODEL", raising=False)
    c = TestClient(app)
    c.post("/student/welcome", data={"family": "엄마, 아빠", "satisfaction": "4", "helpers": ["담임 선생님"]})
    return c


def _fake_llm(monkeypatch, summary: str):
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "test-model")

    def fake(messages, **kw):
        system = messages[0]["content"]
        if "대화 기록" in system:
            return summary
        if "JSON" in system:
            return '{"level": "none", "topic": "none", "summary": ""}'
        return "그랬구나. 무슨 일 있었어?"

    monkeypatch.setattr(llm, "chat", fake)


def test_day_summary_uses_llm_and_falls_back(monkeypatch):
    monkeypatch.delenv("BOKBOK_LLM_MODEL", raising=False)
    assert chatbot.day_summary(["안녕", "심심해"]) == ("복복이와 이야기를 2번 주고받았어.", "rule")
    _fake_llm(monkeypatch, '"급식에 나온 떡볶이가 맛있었다는 이야기를 했어. 🌱"\n덧붙임. 세 번째 문장.')
    assert chatbot.day_summary(["오늘 급식에 떡볶이 나왔어"]) == ("급식에 나온 떡볶이가 맛있었다는 이야기를 했어. 덧붙임.", "llm")
    # 판정처럼 들리는 요약은 쓰지 않음
    _fake_llm(monkeypatch, "학교폭력을 당했다는 이야기를 했어.")
    assert chatbot.day_summary(["애들이 내 가방을 숨겨"])[1] == "rule"


def test_chat_screen_shows_only_today_and_history_groups_by_day(client, monkeypatch):
    # 처음에는 시연용 지난 이틀 치 대화가 들어 있음
    page = client.get("/student/chat").text
    assert "수행평가가 너무 많아" not in page  # 지난 날의 대화는 대화 화면에 없음
    assert "/student/chat/history" in page
    client.post("/api/chat", data={"text": "오늘 급식에 떡볶이 나왔어"})

    history = client.get("/student/chat/history").text
    order = [history.index(label) for label in ("11월 14일", "11월 13일", "11월 12일")]
    assert order == sorted(order)  # 최근 날짜부터
    assert "오늘 급식에 떡볶이 나왔어" in history and "수행평가가 너무 많아" in history
    assert "국어 발표가 걱정된다는 이야기를 했어." in history  # 지난 날의 하루 요약
    assert "복복이와 이야기를 1번 주고받았어." in history  # LLM이 없을 때의 오늘 요약
    assert 'action="/student/chat/safety"' not in history  # 지난 기록에서는 버튼으로 대답하지 않음


def test_summary_is_made_once_and_refreshed_when_more_is_said(client, monkeypatch):
    calls = []
    _fake_llm(monkeypatch, "급식 이야기를 했어.")
    real = llm.chat
    monkeypatch.setattr(llm, "chat", lambda messages, **kw: (calls.append(1) if "대화 기록" in messages[0]["content"] else None) or real(messages, **kw))
    client.get("/student/chat")
    client.post("/api/chat", data={"text": "오늘 급식에 떡볶이 나왔어"})
    assert "급식 이야기를 했어." in client.get("/student/chat/history").text
    client.get("/student/chat/history")
    assert len(calls) == 1  # 다시 열어도 요약을 새로 만들지 않음
    client.post("/api/chat", data={"text": "진짜 맛있었어"})
    client.get("/student/chat/history")
    assert len(calls) == 2  # 그날 한 말이 늘면 요약도 새로
    day = store.load()["chat_days"][TODAY]
    assert day == {"summary": "급식 이야기를 했어.", "count": 2, "source": "llm"}


def test_new_day_starts_a_fresh_conversation(client, monkeypatch):
    monkeypatch.setenv("BOKBOK_TODAY", YESTERDAY)
    client.get("/student/chat")
    client.post("/api/chat", data={"text": "어제 한 이야기야"})
    monkeypatch.setenv("BOKBOK_TODAY", TODAY)
    seen = []
    monkeypatch.setattr(chatbot, "converse", lambda history, text, today: (seen.append(history) or
                        {"text": "응", "kind": "normal", "source": "rule", "risk": [], "help": None}, []))
    client.get("/student/chat")
    client.post("/api/chat", data={"text": "오늘 한 이야기야"})
    assert all(m["date"] == TODAY for m in seen[0])  # 복복이는 오늘 대화만 이어서 봄
    assert "어제 한 이야기야" not in client.get("/student/chat").text
    assert "어제 한 이야기야" in client.get("/student/chat/history").text


def test_student_can_delete_one_day_and_clear_only_today(client):
    client.get("/student/chat")
    client.post("/api/chat", data={"text": "오늘 한 이야기야"})
    client.post("/student/chat/history/delete", data={"date": YESTERDAY})
    state = store.load()
    assert not any(m["date"] == YESTERDAY for m in state["chats"]) and YESTERDAY not in state["chat_days"]
    assert any(m["date"] == "2026-11-12" for m in state["chats"])
    client.get("/student/chat/history")
    client.post("/student/chat/clear", follow_redirects=False)  # 대화 화면의 휴지통은 오늘 대화만 지움
    state = store.load()
    assert not any(m["date"] == TODAY for m in state["chats"]) and TODAY not in state["chat_days"]
    assert any(m["date"] == "2026-11-12" for m in state["chats"])


def test_teacher_never_sees_the_daily_record(client):
    client.get("/student/chat")
    client.post("/api/chat", data={"text": "오늘 급식에 떡볶이 나왔어"})
    client.get("/student/chat/history")
    for url in ["/teacher", "/teacher/alerts", f"/teacher/students/{data.ME_ID}"]:
        page = client.get(url).text
        assert "떡볶이" not in page and "수행평가가 너무 많아" not in page
        assert "국어 발표가 걱정된다는 이야기를 했어." not in page and "chat/history" not in page
