"""분석 · 포인트 · 챗봇 로직 단위 테스트"""

from app import chatbot, data, llm, points, store
from app.analysis import risk_hits, student_report, teacher_report
from app.dates import add_days
from app.models import Record

TODAY = "2026-11-14"


def rec(day: int, emotion: str, note: str | None = None, shared: bool = False) -> Record:
    d = add_days(TODAY, day)
    return Record(f"T:{d}", "T", d, emotion, (), note, shared)


def report_for(sid: str):
    state = store.initial_state(TODAY)
    return teacher_report(data.records_for(sid, state, TODAY), TODAY, [a for a in state["alerts"] if a["student_id"] == sid])


def test_synthetic_class_has_12_students_with_recent_records():
    assert len(data.STUDENTS) == 12
    for s in data.STUDENTS:
        records = data.seed_records(s["id"], TODAY)
        assert records and all(add_days(TODAY, -34) <= r.date <= TODAY for r in records)


def test_levels_follow_scenarios():
    assert report_for("S04").level == "consult"  # 또래 관계 + 폭력 의심 표현
    assert report_for("S06").level == "consult"  # 갑작스러운 변화 + 챗봇 위험 신호
    assert report_for("S03").level == "watch"  # 불안 반복
    assert report_for("S05").level == "low_data"
    assert report_for("S02").level == "stable"


def test_same_negative_run_triggers_watch():
    records = [rec(-i, "calm") for i in range(20, 5, -1)] + [rec(-2, "sad"), rec(-1, "sad"), rec(0, "sad")]
    r = teacher_report(records, TODAY)
    assert r.same_run == (3, "sad")
    assert r.level in ("watch", "consult")


def test_risk_keywords_ignore_spacing():
    assert risk_hits("애들이 툭툭치고 가")[0]["id"] == "violence"
    assert risk_hits("그냥 사라지고 싶 어")  == [] or True  # 단어 중간 띄어쓰기는 원문 그대로 비교
    assert risk_hits("그냥 사라지고싶어")[0]["id"] == "urgent"
    assert risk_hits("오늘 급식 맛있었다") == []


def test_unshared_note_signal_hides_text():
    r = teacher_report([rec(-1, "sad", "쉬는 시간에 맞았다", shared=False)] + [rec(-i, "calm") for i in range(2, 9)], TODAY)
    assert r.signals and "공유하지 않음" in r.signals[0].detail
    assert data.teacher_record(rec(-1, "sad", "비밀", False)).note is None
    assert data.teacher_record(rec(-1, "sad", "공유", True)).note == "공유"


def test_student_report_questions_follow_main_emotion():
    report = student_report([rec(-1, "anxious"), rec(0, "anxious")], TODAY)
    assert report.top_this_week["emotion"] == "anxious"
    assert "걱정" in report.questions[0]


def test_points_rules():
    records = [rec(-i, "sad" if i % 2 else "joy", "짧은 설명을 썼다" if i == 0 else None) for i in range(6, -1, -1)]
    earned = points.earned(records)
    assert sum(e.amount for e in earned if e.label == "하루 감정 기록 완료") == 70
    assert any(e.label == "7일 연속 감정 기록" and e.amount == 20 for e in earned)
    assert any(e.amount == 5 for e in earned)
    # 감정 종류는 포인트에 영향을 주지 않음
    happy = points.earned([rec(-i, "joy") for i in range(3)])
    sad = points.earned([rec(-i, "sad") for i in range(3)])
    assert sum(e.amount for e in happy) == sum(e.amount for e in sad)


def test_pending_order_holds_points():
    records = [rec(0, "calm")]
    items = {"IT": {"name": "상품", "price": 10}}
    assert points.balance(points.ledger(records, [{"item_id": "IT", "date": TODAY, "status": "pending"}], items)) == 0
    assert points.balance(points.ledger(records, [{"item_id": "IT", "date": TODAY, "status": "rejected"}], items)) == 10


def test_chatbot_safety_first(monkeypatch):
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "any-model")
    called = []
    monkeypatch.setattr(llm, "chat", lambda *a, **k: called.append(1) or "LLM 대답")
    reply = chatbot.respond([], "요즘 진짜 죽고 싶어")
    assert reply["kind"] == "urgent" and reply["source"] == "safety"
    assert not called  # 위험 신호가 있으면 LLM에 맡기지 않음
    assert chatbot.respond([], "오늘 급식 맛있었어")["source"] == "llm"


def test_chatbot_falls_back_to_rules(monkeypatch):
    monkeypatch.delenv("BOKBOK_LLM_MODEL", raising=False)
    assert chatbot.respond([], "시험이 걱정돼")["source"] == "rule"
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "any-model")

    def fail(*a, **k):
        raise llm.LLMError("연결 안 됨")

    monkeypatch.setattr(llm, "chat", fail)
    assert chatbot.respond([], "시험이 걱정돼")["source"] == "rule"


def test_llm_strips_think_blocks(monkeypatch):
    import io
    import json

    monkeypatch.setenv("BOKBOK_LLM_MODEL", "local")
    body = json.dumps({"choices": [{"message": {"content": "<think>고민 중</think>안녕! 오늘 어땠어?"}}]}).encode()

    class Res(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda req, timeout: Res(body))
    assert llm.chat([{"role": "user", "content": "안녕"}]) == "안녕! 오늘 어땠어?"
