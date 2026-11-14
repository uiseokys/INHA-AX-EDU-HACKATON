"""상담 신청으로 가는 길: 학생 메뉴에서 어느 화면에서든 바로 갈 수 있어야 함"""

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BOKBOK_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("BOKBOK_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.setenv("BOKBOK_TODAY", "2026-11-14")
    monkeypatch.delenv("BOKBOK_LLM_MODEL", raising=False)
    c = TestClient(app)
    c.post("/student/promise", data={"basic": ["1", "2", "3"], "chat": ["1", "2"]})  # 처음 접속: 약속(동의) → 기본 정보
    c.post("/student/welcome", data={"action": "skip"})
    return c


@pytest.mark.parametrize("path", ["/student/record", "/student/report", "/student/chat", "/student/shop"])
def test_student_menu_leads_to_counsel_request(client, path):
    """오늘 감정 기록 전(홈보다 감정 휠이 먼저 뜰 때)에도 상담 신청으로 갈 수 있어야 함"""
    page = client.get(path).text
    assert page.count('href="/student/counsel"') == 2  # 위쪽 메뉴 + 휴대폰 아래쪽 탭


def test_counsel_menu_is_marked_as_current_page(client):
    page = client.get("/student/counsel").text
    assert len(re.findall(r'<a href="/student/counsel" aria-current="page"', page)) == 2


def test_student_can_request_counsel_from_the_menu_page(client):
    page = client.get("/student/counsel").text
    slot = re.search(r'name="slot_id" value="([^"]+)"', page).group(1)
    client.post("/student/counsel", data={"slot_id": slot, "topic": "친구 관계"})
    after = client.get("/student/counsel").text
    assert "친구 관계" in after and "확인 중" in after
    assert "친구 관계" in client.get("/teacher/counsel").text
