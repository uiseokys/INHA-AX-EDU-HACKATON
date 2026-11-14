import json

import pytest
from fastapi.testclient import TestClient

from app import llm, store
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BOKBOK_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("BOKBOK_TODAY", "2026-11-14")
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "test-model")
    return TestClient(app)


def model_response(monkeypatch, candidates):
    def chat(messages, **kwargs):
        if "감정 후보" in messages[0]["content"] and "JSON" in messages[0]["content"]:
            return json.dumps({"emotions": candidates}, ensure_ascii=False)
        if "JSON" in messages[0]["content"]:
            return '{"level":"none","topic":"none","summary":""}'
        return "어떤 마음인지 같이 이야기해 보자."

    monkeypatch.setattr(llm, "chat", chat)


def test_mixed_emotions_link_to_record_confirmation(client, monkeypatch):
    model_response(monkeypatch, [
        {"emotion": "calm", "evidence": "후련한데"},
        {"emotion": "anxious", "evidence": "결과는 걱정돼"},
    ])
    existing_alerts = store.load()["alerts"]
    html = client.post("/api/chat", data={"text": "시험이 끝나서 후련한데 결과는 걱정돼"}).json()["html"]

    assert 'href="/student/record?e=calm"' in html
    assert 'href="/student/record?e=anxious"' in html
    assert 'href="/student/record?e=anxious"' in client.get("/student/chat").text
    assert store.load()["my_records"] == []
    assert store.load()["alerts"] == existing_alerts
    assert 'id="emo-anxious" class="sr-only" required checked' in client.get("/student/record?e=anxious").text


def test_classifier_uses_recent_student_chat_to_resolve_the_current_message(client, monkeypatch):
    first = "친구들이 나만 빼고 급식 먹으러 가서 속상해"
    current = "오늘도 나만 혼자 먹었어"

    def chat(messages, **kwargs):
        prompt = messages[0]["content"]
        if "감정 후보" in prompt and "JSON" in prompt:
            body = json.loads(messages[-1]["content"])
            if body == {"앞선 발언": [first], "이번 발언": current}:
                return '{"emotions": [{"emotion": "sad", "evidence": "나만 혼자 먹었어"}]}'
            return '{"emotions": []}'
        if "JSON" in prompt:
            return '{"level":"none","topic":"none","summary":""}'
        return "그런 일이 있었구나."

    monkeypatch.setattr(llm, "chat", chat)
    client.post("/api/chat", data={"text": first})
    html = client.post("/api/chat", data={"text": current}).json()["html"]

    assert 'href="/student/record?e=sad"' in html


def test_chat_ignores_emotions_with_invented_evidence_or_unknown_labels(client, monkeypatch):
    model_response(monkeypatch, [
        {"emotion": "sad", "evidence": "마음이 아파"},
        {"emotion": "surprise", "evidence": "놀랐어"},
    ])
    html = client.post("/api/chat", data={"text": "갑자기 방송이 나와서 놀랐어"}).json()["html"]

    assert "같이 이야기해 보자" in html
    assert "/student/record?e=" not in html


def test_urgent_reply_does_not_show_emotion_candidates(client, monkeypatch):
    model_response(monkeypatch, [{"emotion": "sad", "evidence": "슬퍼"}])
    html = client.post("/api/chat", data={"text": "너무 슬퍼. 사라지고 싶어"}).json()["html"]

    assert "/student/chat/safety" in html
    assert "/student/record?e=" not in html
