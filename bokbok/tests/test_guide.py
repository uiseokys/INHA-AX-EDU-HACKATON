"""선생님 화면의 단계별 대응 안내, 학생 도움 화면의 문구 표시"""

import pytest
from fastapi.testclient import TestClient

from app import data
from app.main import app

TODAY = "2026-11-14"
GUIDE = data.SIGNALS["response_guide"]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BOKBOK_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("BOKBOK_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.setenv("BOKBOK_TODAY", TODAY)
    monkeypatch.delenv("BOKBOK_LLM_MODEL", raising=False)
    c = TestClient(app)
    c.post("/student/welcome", data={"action": "skip"})
    return c


def test_guide_has_do_and_dont_for_every_level():
    for level in ("urgent", "issue", "care"):
        assert GUIDE[level]["when"] and len(GUIDE[level]["do"]) >= 3 and len(GUIDE[level]["dont"]) >= 2


def test_urgent_signal_shows_urgent_guide(client):
    client.get("/student/chat")
    client.post("/api/chat", data={"text": "요즘 진짜 죽고 싶어"})
    page = client.get("/teacher/students/S01").text
    assert "이렇게 대응해 주세요" in page and GUIDE["urgent"]["when"] in page
    assert GUIDE["urgent"]["do"][0] in page and "이것은 피해 주세요" in page
    assert GUIDE["issue"]["do"][0] not in page  # 가장 높은 단계의 안내만


def test_issue_signal_shows_issue_guide_and_no_signal_shows_none(client):
    assert "이렇게 대응해 주세요" not in client.get("/teacher/students/S02").text  # 신호가 없는 학생
    client.post("/student/record", data={"emotion": "sad", "note": "쉬는 시간에 애들한테 맞았다"})
    page = client.get("/teacher/students/S01").text
    assert GUIDE["issue"]["when"] in page and GUIDE["issue"]["do"][0] in page
    assert GUIDE["urgent"]["do"][0] not in page


def test_help_pages_no_longer_marked_as_placeholder(client):
    assert "임시 문구" not in client.get("/student/help").text
    for c in data.HELP_CATEGORIES:
        page = client.get(f"/student/help/{c['id']}").text
        assert "임시 문구" not in page and c["situation"][:20] in page
