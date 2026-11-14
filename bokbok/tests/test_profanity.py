"""욕설·비속어 가림: 학생의 말은 글자 수만큼 * 로 바꾸고, 복복이는 욕을 하지 않음"""

import pytest
from fastapi.testclient import TestClient

from app import chatbot, llm, profanity, store
from app.main import app

TODAY = "2026-11-14"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BOKBOK_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("BOKBOK_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.setenv("BOKBOK_TODAY", TODAY)
    monkeypatch.delenv("BOKBOK_LLM_MODEL", raising=False)
    c = TestClient(app)
    c.post("/student/promise", data={"basic": ["1", "2", "3"], "chat": ["1", "2"]})  # 처음 접속: 약속(동의) → 기본 정보
    c.post("/student/welcome", data={"action": "skip"})
    return c


@pytest.mark.parametrize("said, shown", [
    ("아 씨발 짜증나", "아 ** 짜증나"),  # 두 글자 욕은 별 두 개
    ("개새끼", "***"),
    ("ㅅㅂ 진짜", "** 진짜"),
    ("존나 힘들어", "** 힘들어"),
    ("걔가 나보고 병신이라고 했어", "걔가 나보고 **이라고 했어"),
    ("시1발", "***"),  # 사이에 숫자·기호를 끼워 넣어도 가림
    ("씨.발!", "***!"),
    ("FUCK you", "**** you"),
])
def test_profanity_is_masked_by_length(said, shown):
    assert profanity.mask(said) == shown


@pytest.mark.parametrize("said", [
    "수학 시간에 시발점을 배웠어",
    "다시 발표하래",
    "늦게 자지 마",
    "껌을 씹어",
    "고양이 새끼가 태어났어",
    "새끼손가락 걸고 약속했어",
    "엄마를 졸라서 샀어",
    "미친 듯이 뛰었어",
    "오늘 진짜 짜증났어",
])
def test_ordinary_words_are_left_alone(said):
    assert profanity.mask(said) == said
    assert not profanity.has(said)


def test_chat_stores_and_shows_the_masked_words_only(client):
    res = client.post("/api/chat", data={"text": "아 씨발 짜증나"})
    assert "아 ** 짜증나" in res.json()["html"] and "씨발" not in res.json()["html"]
    mine = [m for m in store.load()["chats"] if m["role"] == "me"][-1]
    assert mine["text"] == "아 ** 짜증나"
    page = client.get("/student/chat").text
    assert "아 ** 짜증나" in page and "씨발" not in page


def test_masking_does_not_hide_a_danger_signal(client):
    """욕이 섞여 있어도 위험 신호는 원래 말로 살핌"""
    client.post("/api/chat", data={"text": "씨발 죽고싶어"})
    state = store.load()
    assert [m for m in state["chats"] if m["role"] == "me"][-1]["text"] == "** 죽고싶어"
    assert [m for m in state["chats"] if m["role"] == "bot"][-1]["kind"] == "urgent"
    assert any(a["source"] == "chat" for a in state["alerts"])


def test_bokbok_drops_a_sentence_with_profanity():
    assert chatbot.off_tone("와 존나 힘들었겠다")
    assert chatbot.tidy("아 씨발 진짜 짜증났겠다. 무슨 일 있었어?") == "무슨 일 있었어?"


def test_bokbok_never_swears_even_if_the_model_does(monkeypatch):
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "test-model")
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "씨발 그 새끼 진짜 나쁘네")
    reply, _ = chatbot.converse([], "친구가 내 욕을 했어", TODAY)
    assert reply["text"] and not profanity.has(reply["text"]) and "*" not in reply["text"]


def test_bokbok_is_told_not_to_swear():
    assert "욕" in chatbot.system_prompt()
