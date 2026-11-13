"""분석 로직 · 공유 범위 · 기관 추천 단위 테스트"""

from app import data, store
from app.analysis import analyze, mood_score, summarize
from app.dates import add_days
from app.models import Consent
from app.privacy import teacher_view

TODAY = "2026-11-13"


def test_mood_score_direction():
    assert mood_score("happy", 5) == 5
    assert mood_score("soso", 4) == 3
    assert mood_score("sad", 5) == 1
    assert mood_score("tired", 3) < 3


def test_synthetic_data_covers_eight_students_within_14_days():
    assert len(data.STUDENTS) == 8
    for student in data.STUDENTS:
        logs = data.seed_logs(student["id"], TODAY)
        assert logs
        assert all(add_days(TODAY, -13) <= log.date <= TODAY for log in logs)


def test_peer_case_finds_change_and_evidence():
    insight = analyze(data.seed_logs("S01", TODAY), TODAY)
    assert insight.enough
    assert insight.change.direction == "down"
    assert insight.topics[0].id == "peer"
    assert len(insight.topics[0].evidence) >= 3
    shift = next(c for c in insight.change_points if c.kind == "shift")
    assert shift.note
    assert len(summarize(insight, "student")) > 1


def test_study_case_top_topic_is_study():
    assert analyze(data.seed_logs("S03", TODAY), TODAY).topics[0].id == "study"


def test_stable_case_is_steady():
    assert analyze(data.seed_logs("S02", TODAY), TODAY).change.direction == "steady"


def test_sparse_case_only_gives_guidance():
    insight = analyze(data.seed_logs("S05", TODAY), TODAY)
    assert not insight.enough
    assert len(summarize(insight, "student")) == 1


def test_todays_checkin_appears_as_last_point():
    state = store.initial_state(TODAY)
    before = analyze(data.logs_for("S01", state, TODAY), TODAY).series[-1]
    state["my_logs"].append(
        {"id": f"S01:{TODAY}", "student_id": "S01", "date": TODAY, "emotion": "calm", "intensity": 4, "note": None, "shared": False}
    )
    after = analyze(data.logs_for("S01", state, TODAY), TODAY).series[-1]
    assert before.score is None
    assert after.score == mood_score("calm", 4)


def test_no_consent_means_nothing_reaches_teacher():
    view = teacher_view(data.seed_logs("S08", TODAY), Consent(trend=False, all_notes=False))
    assert view.logs == []


def test_trend_only_consent_strips_unshared_notes():
    logs = data.seed_logs("S04", TODAY)
    view = teacher_view(logs, Consent(trend=True, all_notes=False))
    assert len(view.logs) == len(logs)
    private_notes = [log.note for log in logs if not log.shared and log.note]
    assert private_notes
    visible_notes = {log.note for log in view.logs}
    assert not visible_notes & set(private_notes)


def test_without_trend_consent_only_shared_records_pass():
    logs = data.seed_logs("S06", TODAY)
    view = teacher_view(logs, Consent(trend=False, all_notes=False))
    assert not view.trend_visible
    assert len(view.logs) == sum(1 for log in logs if log.shared)


def test_agency_matching_filters_and_ranks():
    result = data.match_agencies(data.AGENCIES, type_id="wee-center", student_topics=["peer"])
    assert result
    assert all(m["agency"]["type"] == "wee-center" for m in result)
    assert "peer" in result[0]["matched_topics"]
