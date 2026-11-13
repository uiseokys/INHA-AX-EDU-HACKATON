"""화면 단위 테스트: 모든 페이지가 열리는지, 시연 흐름이 끝까지 이어지는지, 공유하지 않은 메모가 새지 않는지"""

import pytest
from fastapi.testclient import TestClient

from app import data, store
from app.main import app

TODAY = "2026-11-13"


@pytest.fixture
def client(tmp_path, monkeypatch):
    # 테스트마다 빈 상태 파일과 고정된 날짜를 사용
    monkeypatch.setenv("SSUDAM_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("SSUDAM_TODAY", TODAY)
    return TestClient(app)


@pytest.mark.parametrize(
    "path",
    ["/", "/student", "/student?edit=checkin", "/student/insights", "/student/support", "/teacher", "/teacher?status=review",
     "/teacher/agencies", "/teacher/agencies?student=S04&type=wee-center&refer=AG04"]
    + [f"/teacher/students/{s['id']}" for s in data.STUDENTS],
)
def test_pages_render(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert "쓰담" in response.text


def test_unknown_student_is_404(client):
    assert client.get("/teacher/students/S99").status_code == 404


def test_demo_flow_from_checkin_to_referral(client):
    # 1~2) 학생 모드 접속, 오늘의 할 일 확인
    home = client.get("/student").text
    assert "영어 단어 20개 외우기" in home
    assert "오늘 기록이 그래프 맨 오른쪽에 반영됐어요" not in home

    # 3~4) 감정을 기록하면 그래프에 반영
    client.post("/student/checkin", data={"emotion": "anxious", "intensity": "4", "note": "발표가 걱정된다"})
    home = client.get("/student").text
    assert "오늘은 불안해요" in home
    assert "오늘 기록이 그래프 맨 오른쪽에 반영됐어요" in home
    assert "4일 연속 기록" in home

    # 5) 상담 지원 요청
    client.post("/student/support", data={"topic": "친구 관계", "message": "조용히 이야기하고 싶어요."})
    assert "요청이 전달됐어요" in client.get("/student/support").text

    # 6) 상담교사 화면에서 요청 확인
    teacher = client.get("/teacher?status=requested").text
    assert "하늘" in teacher and "새 요청" in teacher
    detail = client.get("/teacher/students/S01").text
    assert "조용히 이야기하고 싶어요." in detail

    # 7) 지원기관 추천 화면에서 연결 요청
    agencies = client.get("/teacher/agencies?student=S01").text
    assert "추천 · 또래 관계" in agencies and "가상 기관" in agencies
    client.post("/teacher/agencies/refer", data={"student_id": "S01", "agency_id": "AG04", "note": "관계 회복 프로그램 문의"})
    state = store.load()
    assert state["case_status"]["S01"] == "referred"
    assert "연결 요청됨" in client.get("/teacher/agencies?student=S01").text
    assert "해봄 Wee센터" in client.get("/teacher/students/S01").text


def test_support_request_works_without_any_record_or_field(client):
    client.post("/student/checkin/skip")
    assert "오늘은 쉬어가요" in client.get("/student").text
    client.post("/student/support")
    assert len(store.load()["requests"]) == 1
    assert "메시지 없이 요청" in client.get("/teacher").text


def test_unshared_notes_never_reach_teacher_pages(client):
    private_note = "단톡에서 나만 빼고 약속을 잡은 것 같다"  # S01의 공유하지 않은 메모
    assert private_note in client.get("/student/insights").text

    # 공유 동의가 없으면 교사 화면에 기록이 없음
    assert private_note not in client.get("/teacher/students/S01").text
    assert "학생이 공유한 기록이 없습니다" in client.get("/teacher/students/S01").text

    # 그래프만 공유: 감정·강도는 보이지만 메모는 보이지 않음
    client.post("/student/consent", data={"key": "trend", "on": "1"})
    detail = client.get("/teacher/students/S01").text
    assert "학생이 그래프 공유에 동의했습니다" in detail
    assert private_note not in detail

    # 그 기록만 공유로 표시하면 그 메모만 보임
    log_id = next(log.id for log in data.seed_logs("S01", TODAY) if log.note == private_note)
    client.post("/student/logs/share", data={"log_id": log_id, "shared": "1"})
    detail = client.get("/teacher/students/S01").text
    assert private_note in detail
    assert "무시당하는 기분" not in detail  # 다른 비공유 메모

    # 공유하지 않기로 한 다른 학생(S08)의 메모는 어떤 교사 화면에도 없음
    assert "농구가 재밌었다" not in client.get("/teacher/students/S08").text
    assert "농구가 재밌었다" not in client.get("/teacher").text


def test_todo_reflection_and_previous_goal(client):
    home = client.get("/student").text
    assert "수학 오답노트 3문제 정리하기" in home  # 어제 남긴 목표를 다시 보여 줌

    client.post("/student/goal-result", data={"date": "2026-11-12", "result": "carried"})
    client.post("/student/todos", data={"text": "과학 3단원 복습", "goal": "1"})
    client.post("/student/todos/seed-2/toggle")
    client.post("/student/reflection", data={"moments": ["동아리", "친구"], "tomorrow_goal": "물 한 컵 마시기"})

    state = store.load()
    texts = [t["text"] for t in state["todos"]]
    assert "수학 오답노트 3문제 정리하기" in texts and "과학 3단원 복습" in texts
    assert next(t for t in state["todos"] if t["id"] == "seed-2")["done"] is True
    home = client.get("/student").text
    assert "오늘의 회고를 남겼어요" in home and "물 한 컵 마시기" in home


def test_status_change_and_reset(client):
    client.post("/teacher/students/S04/status", data={"status": "in_progress"})
    assert store.load()["case_status"]["S04"] == "in_progress"
    assert "진행 상태를 ‘지원 진행 중’(으)로 변경" in client.get("/teacher/students/S04").text
    client.post("/reset", data={"next": "/teacher"})
    assert store.load()["case_status"] == {}
