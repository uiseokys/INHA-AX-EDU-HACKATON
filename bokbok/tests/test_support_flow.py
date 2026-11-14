import re

import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app


TODAY = "2026-11-14"
REQUESTS = "/student/counsel/requests"
COUNSEL = "/student/counsel"
TEACHER_COUNSEL = "/teacher/counsel"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BOKBOK_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("BOKBOK_TODAY", TODAY)
    monkeypatch.delenv("BOKBOK_LLM_MODEL", raising=False)
    return TestClient(app)


def test_read_alert_stays_on_teacher_home_until_action_is_completed(client):
    alerts = client.get("/teacher/alerts").text
    alert = re.search(r'action="(/teacher/alerts/[^"/]+)/read"', alerts).group(1)
    client.post(alert + "/read")

    home = client.get("/teacher").text
    assert f'href="/teacher/alerts#{alert.rsplit("/", 1)[1]}"' in home

    plan = {"teacher": "wee", "due": TODAY, "action": "점심시간에 안부 묻기"}
    assert client.post(alert + "/task", data=plan, follow_redirects=False).status_code == 303
    assert "점심시간에 안부 묻기" in client.get("/teacher").text
    assert "Wee클래스 상담 선생님" in client.get("/teacher").text

    task = re.search(r'name="task_id" value="([^"]+)"', client.get("/teacher/alerts").text).group(1)
    assert client.post(alert + "/task/complete", data={"task_id": task}, follow_redirects=False).status_code == 303
    assert "점심시간에 안부 묻기" not in client.get("/teacher").text
    assert "점심시간에 안부 묻기" in client.get("/teacher/alerts").text


def test_invalid_or_missing_alert_plan_cannot_be_completed(client):
    alerts = client.get("/teacher/alerts").text
    alert = re.search(r'action="(/teacher/alerts/[^"/]+)/read"', alerts).group(1)
    assert client.post(alert + "/task/complete").status_code == 409
    response = client.post(alert + "/task", data={"teacher": "wee", "due": "2026-02-31", "action": "안부 묻기"})
    assert response.status_code == 400
    assert "안부 묻기" not in client.get("/teacher").text


def send_request(client, teacher="homeroom"):
    reply = client.post(REQUESTS, data={"teacher": teacher}, follow_redirects=False)
    assert reply.status_code == 303
    page = client.get(TEACHER_COUNSEL).text
    paths = re.findall(r'action="(/teacher/counsel/requests/[^"/]+)/acknowledge"', page)
    assert len(paths) == 1
    return paths[0]


def test_student_can_request_a_conversation_without_available_slots(client):
    for index in range(5):
        client.post(f"{TEACHER_COUNSEL}/slots/SL-homeroom-{index}/delete")
    page = client.get(COUNSEL).text
    assert f'action="{REQUESTS}"' in page
    assert 'name="slot_id" value="SL-homeroom-' not in page

    request = send_request(client)
    assert "요청 보냄" in client.get(COUNSEL).text
    assert "대화 요청" in client.get("/teacher").text
    request_id = request.rsplit("/", 1)[1]
    client.post(request + "/acknowledge")
    assert "선생님이 확인함" in client.get(COUNSEL).text

    offered = {"date": "2026-11-16", "time": "13:25"}
    assert client.post(request + "/propose", data=offered, follow_redirects=False).status_code == 303
    page = client.get(COUNSEL).text
    assert "이야기할 시간 제안" in page and "13:25" in page
    assert f'action="{REQUESTS}/{request_id}/accept"' in page

    accept = f"{REQUESTS}/{request_id}/accept"
    for _ in range(2):
        assert client.post(accept, data={"slot": "2026-11-16T13:25"}, follow_redirects=False).status_code == 303
    assert client.get(COUNSEL).text.count("13:25") == 1
    assert "확정" in client.get(COUNSEL).text
    assert "13:25" in client.get(TEACHER_COUNSEL).text


def test_proposed_slot_cannot_be_booked_until_student_requests_another_time(client):
    request = send_request(client)
    request_id = request.rsplit("/", 1)[1]
    client.post(request + "/acknowledge")
    client.post(request + "/propose", data={"date": "2026-11-15", "time": "08:20"})
    slot = {"slot_id": "SL-homeroom-0"}
    assert "slot_taken" in client.post(COUNSEL, data=slot, follow_redirects=False).headers["location"]

    assert client.post(f"{REQUESTS}/{request_id}/another-time", data={"slot": "2026-11-15T08:20"}, follow_redirects=False).status_code == 303
    assert "booked" in client.post(COUNSEL, data=slot, follow_redirects=False).headers["location"]


def test_repeated_request_does_not_create_duplicate_work_for_teacher(client):
    request = send_request(client, teacher="wee")
    assert send_request(client, teacher="wee") == request


def test_teacher_cannot_propose_a_time_student_already_booked_with_someone_else(client):
    assert "booked" in client.post(COUNSEL, data={"slot_id": "SL-homeroom-0"}, follow_redirects=False).headers["location"]
    request = send_request(client, teacher="wee")
    client.post(request + "/acknowledge")
    response = client.post(request + "/propose", data={"date": "2026-11-15", "time": "08:20"}, follow_redirects=False)
    assert "conversation_taken" in response.headers["location"]
    assert "선생님이 확인함" in client.get(COUNSEL).text


def test_stale_alert_tab_cannot_complete_an_edited_plan(client):
    alert = "/teacher/alerts/AL-S06"
    plan = {"teacher": "wee", "due": TODAY, "action": "조치 첫 번째"}
    client.post(alert + "/task", data=plan)
    task = re.search(r'name="task_id" value="([^"]+)"', client.get("/teacher/alerts").text).group(1)
    client.post(alert + "/task", data={**plan, "action": "조치 두 번째"})
    assert client.post(alert + "/task/complete", data={"task_id": task}).status_code == 409
    assert "조치 두 번째" in client.get("/teacher").text


def test_new_urgent_signal_reopens_completed_alert(client):
    with store.editing() as state:
        state["alerts"] = [{
            "id": "AL-test", "student_id": "S01", "source": "record", "category": "signal", "date": TODAY,
            "time": "09:00", "summary": "이전 신호", "level": "issue", "read": True,
            "task": {"id": "AT-test", "teacher": "wee", "due": TODAY, "action": "기존 조치", "completed_at": "09:30"},
        }]
    client.post("/student/record", data={"emotion": "sad", "note": "죽고 싶어"})
    home = client.get("/teacher").text
    assert 'href="/teacher/alerts#AL-test"' in home
    assert "기존 조치" not in home
