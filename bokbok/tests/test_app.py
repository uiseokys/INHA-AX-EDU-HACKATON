"""화면 단위 테스트: 모든 페이지가 열리는지, 기획서의 흐름이 끝까지 이어지는지"""

import pytest
from fastapi.testclient import TestClient

from app import data, store
from app.main import app

TODAY = "2026-11-14"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BOKBOK_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("BOKBOK_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.setenv("BOKBOK_TODAY", TODAY)
    monkeypatch.delenv("BOKBOK_LLM_MODEL", raising=False)
    return TestClient(app)


def onboard(client):
    client.post("/student/welcome", data={"family": "엄마, 아빠", "satisfaction": "4", "helpers": ["담임 선생님"]})


STUDENT_PAGES = ["/student", "/student/record", "/student/record?e=sad", "/student/report", "/student/chat", "/student/help",
                 "/student/counsel", "/student/counsel?teacher=wee", "/student/shop", "/student/points", "/student/welcome?edit=1"]
TEACHER_PAGES = ["/teacher", "/teacher?level=consult", "/teacher/alerts", "/teacher/counsel", "/teacher/shop",
                 "/teacher/shop?edit=new", "/teacher/shop?edit=IT1"] + [f"/teacher/students/{s['id']}" for s in data.STUDENTS]


@pytest.mark.parametrize("path", ["/", "/student/welcome"] + [f"/student/help/{c['id']}" for c in data.HELP_CATEGORIES])
def test_public_pages(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", STUDENT_PAGES + TEACHER_PAGES)
def test_pages_render(client, path):
    onboard(client)
    res = client.get(path)
    assert res.status_code == 200, res.text[:500]
    assert "복복" in res.text


def test_first_visit_goes_to_onboarding_and_skip_works(client):
    res = client.get("/student", follow_redirects=False)
    assert res.headers["location"] == "/student/welcome"
    client.post("/student/welcome", data={"action": "skip"})
    assert client.get("/student", follow_redirects=False).status_code == 200


def test_profile_visible_to_teacher(client):
    onboard(client)
    page = client.get("/teacher/students/S01").text
    assert "엄마, 아빠" in page and "담임 선생님" in page


def test_record_flow_points_and_chat_suggestion(client):
    onboard(client)
    before = client.get("/student/points").text
    client.post("/student/record", data={"emotion": "sad", "words": ["속상한", "외로운"], "note": "친구가 내 말을 무시했다"})
    home = client.get("/student?saved=1").text
    assert "기록 완료! 포인트를 받았어요" in home
    assert "+10P" in home and "+5P" in home
    assert "지금은 괜찮아요" in home  # 부정 감정이면 복복이 대화 권유
    assert "속상한" in client.get("/student").text
    assert before != client.get("/student/points").text


def test_positive_record_has_no_chat_suggestion(client):
    onboard(client)
    client.post("/student/record", data={"emotion": "joy", "words": ["신나는"]})
    assert "지금은 괜찮아요" not in client.get("/student?saved=1").text


def test_chat_risk_creates_alert_without_text(client):
    onboard(client)
    client.get("/student/chat")
    res = client.post("/api/chat", data={"text": "다 끝내고 싶어. 사라지고 싶어"})
    assert "109" in res.json()["html"]
    state = store.load()
    alert = [a for a in state["alerts"] if a["student_id"] == "S01"][-1]
    assert alert["source"] == "chat" and "사라지고" not in alert["summary"]
    teacher = client.get("/teacher").text
    assert "하늘 학생" in teacher  # 상단 고정 알림
    assert "사라지고 싶어" not in teacher
    assert "사라지고 싶어" not in client.get("/teacher/students/S01").text
    assert "상담 권장" in client.get("/teacher/students/S01").text


def test_chat_normal_reply_and_form_fallback(client):
    onboard(client)
    client.post("/student/chat", data={"text": "시험이 너무 걱정돼"})
    page = client.get("/student/chat").text
    assert "시험이 너무 걱정돼" in page and "규칙 기반 응답" in page


def test_unsafe_answer_alerts_teacher(client):
    onboard(client)
    client.post("/student/chat/safety", data={"answer": "no"})
    assert any(a["category"] == "unsafe" for a in store.load()["alerts"])
    assert "112" in client.get("/student/chat").text


def test_record_risk_note_alert(client):
    onboard(client)
    client.post("/student/record", data={"emotion": "sad", "note": "쉬는 시간에 애들한테 맞았다"})
    alert = [a for a in store.load()["alerts"] if a["student_id"] == "S01"][-1]
    assert alert["source"] == "record" and "맞았다" not in alert["summary"]


def test_counsel_booking_flow(client):
    onboard(client)
    slot = store.load()["slots"]["homeroom"][0]
    client.post("/student/counsel", data={"slot_id": slot["id"], "topic": "친구 관계"})
    booking = [b for b in store.load()["bookings"] if b["student_id"] == "S01"][0]
    assert booking["status"] == "requested"
    # 같은 시간은 다시 신청할 수 없음
    assert "slot_taken" in client.post("/student/counsel", data={"slot_id": slot["id"]}, follow_redirects=False).headers["location"]
    client.post(f"/teacher/counsel/bookings/{booking['id']}", data={"status": "confirmed"})
    assert "확정" in client.get("/student/counsel").text
    assert store.load()["followups"]["S01"] == "talking"


def test_teacher_adds_slot(client):
    client.post("/teacher/counsel/slots", data={"teacher": "wee", "date": "2026-11-20", "time": "17:00"})
    assert any(s["date"] == "2026-11-20" for s in store.load()["slots"]["wee"])


def test_shop_order_approval_flow(client):
    onboard(client)
    client.post("/student/shop/IT4")
    order = [o for o in store.load()["orders"] if o["student_id"] == "S01"][0]
    assert order["status"] == "pending"
    assert "승인 대기" in client.get("/student/shop").text
    client.post(f"/teacher/shop/orders/{order['id']}", data={"decision": "approved"})
    assert "음악 선택권 교환" in client.get("/student/points").text
    # 품절 상품은 신청 불가
    assert "not_enough" in client.post("/student/shop/IT5", follow_redirects=False).headers["location"]


def test_teacher_item_with_image(client):
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    client.post("/teacher/shop/items", data={"name": "칭찬 스티커", "price": "30", "limit": "5", "on_sale": "1"},
                files={"image": ("s.png", png, "image/png")})
    item = [i for i in store.load()["items"] if i["name"] == "칭찬 스티커"][0]
    assert item["image"] and client.get(f"/uploads/{item['image']}").status_code == 200
    assert "칭찬 스티커" in client.get("/student/shop").text
    bad = client.post("/teacher/shop/items", data={"name": "x"}, files={"image": ("a.txt", b"hi", "text/plain")}, follow_redirects=False)
    assert "bad_image" in bad.headers["location"]


def test_followup_marks_alerts_read(client):
    assert "다온 학생" in client.get("/teacher").text
    client.post("/teacher/students/S06/followup", data={"status": "checked", "note": "보건실에서 안부 확인"})
    state = store.load()
    assert all(a["read"] for a in state["alerts"] if a["student_id"] == "S06")
    assert "보건실에서 안부 확인" in client.get("/teacher/students/S06").text


def test_reset(client):
    onboard(client)
    client.post("/reset", data={"next": "/teacher"})
    assert store.load()["profile"] is None
