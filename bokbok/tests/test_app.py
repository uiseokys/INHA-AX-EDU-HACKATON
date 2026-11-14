"""화면 단위 테스트: 모든 페이지가 열리는지, 기획서의 흐름이 끝까지 이어지는지"""

import re

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
    assert client.get("/student", follow_redirects=False).headers["location"] == "/student/record"


def test_profile_visible_to_teacher(client):
    onboard(client)
    page = client.get("/teacher/students/S01").text
    assert "엄마, 아빠" in page and "담임 선생님" in page


def test_emotion_calendar_displays_school_events_and_own_assessments(client):
    page = client.get("/student/report").text
    assert 'id="emotion-calendar"' in page
    calendar = page.split('id="emotion-calendar"', 1)[1].split("</section>", 1)[0]
    assert "11월 감정 달력" in calendar
    sports_day = re.search(r'<div[^>]+data-calendar-date="2026-11-06"[^>]*>(.*?)</div>', calendar, re.S)
    assert sports_day and "불안 스티커" in sports_day[1]
    assert 'href="#school-schedule-2026-11-06"' in sports_day[1] and "체육대회" in sports_day[1]
    assert 'href="#school-schedule-2026-11-20"' in calendar and "현장체험학습" in calendar
    assert 'href="#school-schedule-2026-11-09"' in calendar and "영어 단원평가" in calendar
    assert 'href="#school-schedule-2026-11-12"' in calendar and "영어 단원평가 결과 공개" in calendar
    assert "수학 단원평가" not in calendar and "84점" not in calendar


def test_school_calendar_only_shows_events_in_displayed_month(client, monkeypatch):
    monkeypatch.setenv("BOKBOK_TODAY", "2026-12-01")
    page = client.get("/student/report").text
    assert "12월 감정 달력" in page
    assert "체육대회" not in page and "현장체험학습" not in page


def test_teacher_can_compare_attendance_with_emotion(client):
    dashboard = client.get("/teacher").text
    assert "출석률 70%" in dashboard
    detail = client.get("/teacher/students/S04").text
    assert "출석률 변화" in detail and "직전 수업일 10일" in detail
    assert "70%" in detail and "100%" in detail
    assert "출석률 하락과 힘든 날이 함께 나타남" in detail


def test_teacher_chart_renders_attendance_and_independent_controls(client):
    detail = client.get("/teacher/students/S04").text
    assert "감정과 출석률 변화" in detail
    for series in ("emotion", "average", "attendance"):
        assert re.search(rf'<input[^>]+data-chart-toggle="{series}"[^>]+checked', detail)
        assert f'data-chart-layer="{series}"' in detail
    assert 'aria-label="11/13(금) 출석률 70% · 결석"' in detail
    assert 'aria-label="11/14(토) 출석률' not in detail
    assert 'data-chart-toggle="attendance"' not in client.get("/student/report").text


def test_teacher_sees_assessment_dates_and_comparison_without_changing_status(client, monkeypatch):
    path = "/teacher/students/S04"
    detail = client.get(path).text
    assert re.search(r'<input[^>]+data-chart-toggle="assessment"[^>]+checked', detail)
    assert 'aria-label="11/3(화) 시험일 · 수학 단원평가"' in detail
    assert 'aria-label="11/6(금) 결과 공개 · 수학 단원평가"' in detail
    assert "82점 → 71점" in re.sub(r"<[^>]+>", "", detail)
    assert "수학 단원평가 결과를 받은 주에 불안 기록이 늘었어요" in detail
    assert 'data-chart-toggle="assessment"' not in client.get("/student/report").text

    monkeypatch.setattr(data, "assessments_for", lambda student_id, today: [])
    without_assessments = client.get(path).text
    level = r'<p class="mt-1 text-sm text-ink">([^<]+)</p>'
    assert re.search(level, detail)[1] == re.search(level, without_assessments)[1]
    assert 'data-chart-layer="assessment"' not in without_assessments


def test_synthetic_attendance_excludes_weekends_and_today():
    days = data.attendance_for("S04", "2026-11-16")  # 월요일
    dates = [day.date for day in days]
    assert len(dates) == len(set(dates)) == 20
    assert dates[-3:] == ["2026-11-11", "2026-11-12", "2026-11-13"]
    assert "2026-11-07" not in dates and "2026-11-08" not in dates


def test_teacher_shares_support_note_with_colleague(client):
    path = "/teacher/students/S01"
    personal = "시험 공부 때문에 답답했던 마음, 오늘 일기 비공개 원문 예시"
    note = "이번 주 중 학생과 짧게 안부 확인을 부탁드립니다."
    onboard(client)
    client.post("/student/record", data={"emotion": "sad", "note": personal})
    detail = client.get(path).text
    assert personal not in detail
    assert "학업·시험 관련 고민" not in detail
    assert 'action="/teacher/students/S01/shares"' in detail
    sent = client.post(path + "/shares", data={"sender": "homeroom", "recipient": "wee", "note": note})
    assert "지원 메모를 공유했어요" in sent.text

    recipient = client.get("/teacher/shares?teacher=wee").text
    assert "하늘" in recipient and "김다정 선생님" in recipient and note in recipient
    assert personal not in recipient
    sender = client.get("/teacher/shares?teacher=homeroom").text
    assert "보낸 메모" in sender and "박온유 선생님" in sender and note in sender
    for url in ("/student", "/student/report", "/student/chat", "/teacher/students/S02"):
        assert note not in client.get(url).text


@pytest.mark.parametrize("sender, recipient, note", [
    ("student", "wee", "잘못된 발신 정보"),
    ("wee", "wee", "자기 자신에게 보내기"),
    ("homeroom", "wee", "  "),
])
def test_teacher_share_rejects_invalid_submission(client, sender, recipient, note):
    result = client.post("/teacher/students/S01/shares", data={"sender": sender, "recipient": recipient, "note": note},
                         follow_redirects=False)
    assert result.status_code == 400


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


@pytest.mark.parametrize(("emotion", "intensity", "label"), [
    ("anxious", "4", "불안 · 많이"),
    ("joy", "5", "기쁨 · 아주 많이"),
    ("calm", "", "평온"),
])
def test_start_chat_with_today_emotion(client, emotion, intensity, label):
    onboard(client)
    private_note = "이 일기 문장은 대화에 넣지 않아요."
    saved = client.post("/student/record", data={"emotion": emotion, "intensity": intensity, "note": private_note})
    form = re.search(r'<form[^>]+action="([^"]+)"[^>]*>\s*<button[^>]*>오늘 감정으로 이야기하기</button>', saved.text)
    assert form is not None

    plain_chat = client.get("/student/chat").text
    assert "오늘 기록" not in plain_chat
    chat = client.post(form[1]).text
    assert f"‘{label}’" in chat and "지금도 그 마음에 대해 이야기하고 싶어?" in chat
    assert chat.count('data-role="bot"') == 1
    assert private_note not in chat
    assert not any(a["source"] == "chat" and a["student_id"] == data.ME_ID for a in store.load()["alerts"])
    assert client.post(form[1]).text.count(f"‘{label}’") == 1


def test_today_emotion_opener_stays_out_of_alert_model(client, monkeypatch):
    from app import llm

    onboard(client)
    client.post("/student/record", data={"emotion": "angry", "intensity": "3", "words": ["억울한"],
                                         "note": "일기 원문 확인 문장"})
    client.post("/student/chat/today-emotion")

    calls = []

    def reply(messages, **kwargs):
        calls.append(messages)
        if "JSON" in messages[0]["content"]:
            return '{"level": "none", "topic": "mind", "summary": ""}'
        return "지금은 편하다니 다행이야."

    monkeypatch.setenv("BOKBOK_LLM_MODEL", "test-model")
    monkeypatch.setattr(llm, "chat", reply)
    result = client.post("/api/chat", data={"text": "지금은 편해"})
    assert "지금은 편하다니 다행이야." in result.json()["html"]
    conversation, assessment, emotions = calls
    assert "학생이 지금 한 말을 우선해" in conversation[0]["content"]
    assert any(m["role"] == "assistant" and "분노 · 보통" in m["content"] for m in conversation)
    assert conversation[-1] == {"role": "user", "content": "지금은 편해"}
    assert "분노 · 보통" not in str(assessment)
    assert "분노 · 보통" not in str(emotions)
    assert "지금은 편해" in str(emotions)
    assert "일기 원문 확인 문장" not in str(calls)
    assert "억울한" not in str(calls)


def test_starting_from_emotion_keeps_todays_existing_chat(client):
    onboard(client)
    client.get("/student/chat")
    client.post("/student/chat", data={"text": "급식이 맛있었어"})
    client.post("/student/record", data={"emotion": "joy", "intensity": "3"})

    chat = client.post("/student/chat/today-emotion").text
    assert chat.index("급식이 맛있었어") < chat.index("‘기쁨 · 보통’")
    assert client.post("/student/chat/today-emotion").text.count("‘기쁨 · 보통’") == 1


def test_today_emotion_prompts_use_only_todays_record(client, monkeypatch):
    onboard(client)
    client.post("/student/record", data={"emotion": "joy", "intensity": "4"})
    monkeypatch.setenv("BOKBOK_TODAY", "2026-11-15")
    chat = client.post("/student/chat/today-emotion")
    assert chat.status_code == 200 and chat.url.path == "/student/chat"
    assert "오늘 기록" not in chat.text


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
    assert (alert["category"], alert["level"]) == ("signal", "issue") and "폭력" not in alert["summary"]
    page = client.get("/teacher/students/S01").text
    assert "감정 기록에서 위험 신호가 감지되었어요" in page and "폭력 피해가 의심되는 표현" not in page


def test_home_opens_emotion_wheel_until_today_is_recorded(client):
    onboard(client)
    res = client.get("/student", follow_redirects=False)
    assert res.status_code == 303 and res.headers["location"] == "/student/record"
    client.post("/student/record", data={"emotion": "joy"})
    assert client.get("/student", follow_redirects=False).status_code == 200


def test_student_can_put_off_todays_record(client):
    onboard(client)
    assert "나중에 할게요" in client.get("/student/record").text
    res = client.post("/student/record/later", data={"emotion": "sad", "intensity": "3"}, follow_redirects=False)
    assert res.status_code == 303 and res.headers["location"] == "/student"
    assert store.load()["my_records"] == []  # 고르던 내용은 기록으로 남지 않음
    home = client.get("/student", follow_redirects=False)
    assert home.status_code == 200
    assert "오늘 마음 기록하기" in home.text
    assert 'href="/student/record?e=' not in home.text  # 홈에서 스티커를 또 고르게 하지 않음


def test_putting_off_lasts_only_for_that_day(client, monkeypatch):
    onboard(client)
    client.post("/student/record/later")
    monkeypatch.setenv("BOKBOK_TODAY", "2026-11-15")
    assert client.get("/student", follow_redirects=False).headers["location"] == "/student/record"


def test_record_page_offers_back_instead_of_later_once_recorded(client):
    onboard(client)
    client.post("/student/record", data={"emotion": "joy"})
    page = client.get("/student/record").text
    assert 'aria-label="홈으로"' in page and "나중에 할게요" not in page


def test_record_saves_and_shows_intensity(client):
    onboard(client)
    client.post("/student/record", data={"emotion": "sad", "words": ["속상한"], "intensity": "4"})
    assert store.load()["my_records"][-1]["intensity"] == 4
    for path in ["/student", "/student/report", f"/teacher/students/{data.ME_ID}"]:
        assert "강도 4" in client.get(path).text, path


@pytest.mark.parametrize("raw, saved", [("3", 3), ("0", 1), ("9", 5), ("abc", None), ("", None),
                                        ("3.5", None), (" 4 ", 4), ("-2", 1)])
def test_record_intensity_is_clamped(client, raw, saved):
    onboard(client)
    res = client.post("/student/record", data={"emotion": "joy", "intensity": raw}, follow_redirects=False)
    assert res.status_code == 303
    assert store.load()["my_records"][-1]["intensity"] == saved


def test_old_record_without_intensity_still_renders(client):
    onboard(client)
    client.post("/student/record", data={"emotion": "sad"})
    with store.editing() as state:
        state["my_records"][-1].pop("intensity")
    for path in ["/student", "/student/record", "/student/report", f"/teacher/students/{data.ME_ID}"]:
        assert client.get(path).status_code == 200, path
    assert "강도 " not in client.get("/student").text


def test_record_page_prefills_intensity(client):
    onboard(client)
    client.post("/student/record", data={"emotion": "sad", "intensity": "5"})
    assert re.search(r'name="intensity"[^>]*value="5"', client.get("/student/record").text)


def test_record_page_is_emotion_wheel(client):
    onboard(client)
    page = client.get("/student/record").text
    assert "오늘 마음은 어땠나요?" in page and "가장 가까운 스티커를 눌러 보세요." in page
    assert "‘슬픔’에 가까운 마음을 골라 주세요" in page
    assert page.count('name="emotion"') == 5 and page.count('name="words"') == 40
    assert re.search(r'name="intensity"[^>]*value="3"', page)
    assert "다시 고르기" in page and "기록하고 포인트 받기" in page
    assert "강도는 선생님 리포트에 쓰여요" in page


def test_record_page_preselects_sticker_from_home(client):
    onboard(client)
    assert re.search(r'id="emo-sad"[^>]*checked', client.get("/student/record?e=sad").text)


def test_script_address_changes_when_script_changes(client):
    """브라우저가 예전 app.js 를 계속 쓰면 강도 고리가 뜨지 않으므로, 주소에 파일 수정 시각을 붙임"""
    onboard(client)
    assert re.search(r'src="/static/app\.js\?v=\d+"', client.get("/student/record").text)


def test_reset_link_reopens_wheel_without_script(client):
    """스크립트 없이 오늘 기록을 고칠 때도 '다시 고르기'로 다른 스티커를 고를 수 있어야 함"""
    onboard(client)
    client.post("/student/record", data={"emotion": "sad"})
    assert 'href="/student/record?e=none"' in client.get("/student/record").text
    assert not re.search(r'name="emotion"[^>]*checked', client.get("/student/record?e=none").text)


def test_dial_takes_touches_only_on_its_ring(client):
    """고리 안쪽(가운데 스티커)과 네 귀퉁이를 쓸어 넘겨도 화면이 스크롤되도록, 누르는 영역을 고리 띠로 한정"""
    onboard(client)
    assert "data-dial-hit" in client.get("/student/record").text


def test_ring_instruction_is_shown_only_when_the_ring_is(client):
    onboard(client)
    page = client.get("/student/record").text
    assert '<span class="wheel-dial-only">고리를 돌려 </span>강도를 정하고, 단어를 눌러 보세요.' in page


def test_dial_starts_unset_until_the_student_chooses(client):
    """건드리지 않은 다이얼이 '강도 3'으로 저장돼 선생님께 일부러 고른 값처럼 보이지 않게 함"""
    onboard(client)
    page = client.get("/student/record").text
    assert "data-unset" in page and "고리를 돌려 정해 보세요" in page


def test_dial_shows_saved_intensity_only_for_the_same_sticker(client):
    onboard(client)
    client.post("/student/record", data={"emotion": "sad", "intensity": "5"})
    same = client.get("/student/record").text
    assert "data-unset" not in same and re.search(r'name="intensity"[^>]*value="5"', same)
    other = client.get("/student/record?e=joy").text
    assert "data-unset" in other and re.search(r'name="intensity"[^>]*value="3"', other)


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


def test_chat_signal_reaches_teacher_silently(client, monkeypatch):
    """도움이 필요해 보이면 학생 화면에는 아무 표시 없이, 선생님께 '신호가 있다'는 사실과 단계만 전해진다"""
    from app import llm
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "test-model")
    note = "친구들이 자신만 빼고 대화방을 만들었다고 이야기함."
    verdict = '{"level": "issue", "topic": "school", "summary": "%s"}' % note
    monkeypatch.setattr(llm, "chat", lambda messages, **k: verdict if "JSON" in messages[0]["content"] else "헐, 속상했겠다.")
    onboard(client)
    client.get("/student/chat")
    html = client.post("/api/chat", data={"text": "나만 빼고 단톡방 만들었대"}).json()["html"]
    assert "헐, 속상했겠다." in html
    assert "선생님" not in html and "알렸" not in html  # 학생에게는 알리지 않음
    alert = [a for a in store.load()["alerts"] if a["student_id"] == "S01"][-1]
    # 무슨 이야기였는지(분류·AI 요약)는 저장하지도 않음
    assert (alert["source"], alert["category"], alert["level"], alert["note"]) == ("chat", "signal", "issue", None)
    for url in ("/teacher", "/teacher/alerts", "/teacher/students/S01"):
        page = client.get(url).text
        assert "위험 신호가 감지되었어요" in page and "확인 필요" in page
        assert note not in page and "대화방" not in page  # 무슨 이야기였는지는 보이지 않음
        assert "나만 빼고 단톡방 만들었대" not in page and "원문은 전해지지" not in page
    assert "상담 권장" in client.get("/teacher/students/S01").text
    # 같은 날에는 대화 신호 알림을 하나만 둠
    client.post("/api/chat", data={"text": "말 걸어도 무시해"})
    assert len([a for a in store.load()["alerts"] if a["student_id"] == "S01" and a["source"] == "chat"]) == 1


def test_care_level_is_watch_not_consult(client, monkeypatch):
    from app import llm
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "test-model")
    verdict = '{"level": "care", "topic": "mind", "summary": "요즘 계속 힘들다고 이야기함."}'
    monkeypatch.setattr(llm, "chat", lambda messages, **k: verdict if "JSON" in messages[0]["content"] else "그랬구나.")
    onboard(client)
    client.get("/student/chat")
    for text in ("요즘 아무것도 하기 싫어", "잠도 안 와", "그냥 계속 그래"):
        client.post("/api/chat", data={"text": text})
    alerts = [a for a in store.load()["alerts"] if a["student_id"] == "S01"]
    assert [(a["category"], a["level"], a["note"]) for a in alerts] == [("signal", "care", None)]
    page = client.get("/teacher/students/S01").text
    assert "살펴보기" in page and "복복이 대화에서 살펴볼 신호" in page and "힘들다고 이야기함" not in page


def test_keyword_signal_without_llm_keeps_conversation_going(client):
    onboard(client)
    client.get("/student/chat")
    html = client.post("/api/chat", data={"text": "쉬는 시간에 애들한테 맞았어"}).json()["html"]
    assert "/student/help/school-violence" in html and "109" not in html and "선생님" not in html
    alert = [a for a in store.load()["alerts"] if a["student_id"] == "S01"][-1]
    assert (alert["category"], alert["level"], alert["note"]) == ("signal", "issue", None)
    assert "폭력 피해가 의심되는 표현" not in client.get("/teacher/students/S01").text  # 키워드 분류도 선생님께 보이지 않음


def test_chat_signal_escalates_within_one_alert(client, monkeypatch):
    """같은 날 살펴보기 → 긴급으로 올라가면 알림은 하나로 두고 단계만 올림"""
    from app import llm
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "test-model")
    verdict = {"v": '{"level": "issue", "topic": "school", "summary": "무시당한다고 이야기함."}'}
    monkeypatch.setattr(llm, "chat", lambda messages, **k: verdict["v"] if "JSON" in messages[0]["content"] else "그랬구나.")
    onboard(client)
    client.get("/student/chat")
    client.post("/api/chat", data={"text": "말 걸어도 다 무시해"})
    verdict["v"] = '{"level": "urgent", "topic": "mind", "summary": "깨어나지 않았으면 좋겠다고 이야기함."}'
    client.post("/api/chat", data={"text": "눈 감으면 안 깼으면 좋겠어"})
    alerts = [a for a in store.load()["alerts"] if a["student_id"] == "S01" and a["source"] == "chat"]
    assert [(a["category"], a["level"], a["read"]) for a in alerts] == [("signal", "urgent", False)]
    page = client.get("/teacher/students/S01").text
    assert "긴급" in page and "깨어나지" not in page and "자해" not in page
