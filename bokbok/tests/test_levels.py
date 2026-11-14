"""학생 상태(양호·주의·심각) 기준: 하루 기록을 감정과 강도로 나누고, 최근 7일로 판단"""

from app.analysis import day_kind, teacher_report
from app.dates import add_days
from app.models import Record

TODAY = "2026-11-14"


def rec(offset: int, emotion: str, intensity: int | None = None) -> Record:
    d = add_days(TODAY, offset)
    return Record(id=f"T:{d}", student_id="T", date=d, emotion=emotion, intensity=intensity)


def month(recent: list[tuple[str, int | None]]) -> list[Record]:
    """지난 28일은 평온(강도 3)으로 채우고, 최근 7일(-6 ~ 0)에 recent 를 차례로 넣음"""
    calm = [rec(off, "calm", 3) for off in range(-34, -6)]
    return calm + [rec(off, e, n) for off, (e, n) in zip(range(-6, 1), recent)]


def level(recent) -> str:
    return teacher_report(month(recent), TODAY).level


def test_day_kind_uses_emotion_and_intensity():
    assert [day_kind(rec(0, "joy", n)) for n in (1, 3, 5)] == ["good"] * 3
    assert [day_kind(rec(0, "sad", n)) for n in (1, 2, 3, 4, 5)] == ["ok", "ok", "hard", "very_hard", "very_hard"]
    assert day_kind(rec(0, "angry", None)) == "hard"  # 강도가 없는 예전 기록은 3으로 봄


def test_one_very_hard_day_does_not_raise_level():
    assert level([("calm", 3)] * 6 + [("angry", 5)]) == "stable"


def test_mild_negative_days_stay_stable():
    """가벼운 부정 감정은 매일 이어져도 '보통 날'"""
    r = teacher_report(month([("anxious", 2), ("calm", 3)] * 3 + [("anxious", 1)]), TODAY)
    assert r.level == "stable" and r.week_kinds == {"good": 3, "ok": 4, "hard": 0, "very_hard": 0}
    assert r.same_run == (0, None)


def test_attendance_change_needs_emotion_evidence_to_raise_level():
    from app.attendance import AttendanceDay, attendance_summary

    days = [AttendanceDay(add_days(TODAY, offset), status)
            for offset, status in zip(range(-24, 1), ["present"] * 22 + ["absent", "present", "absent"])]
    attendance = attendance_summary(days, TODAY)
    assert attendance.previous.rate == 100 and attendance.recent.rate == 80
    calm = [("calm", 3)] * 7
    report = teacher_report(month(calm), TODAY, attendance=attendance)
    assert report.level == "stable"
    assert any("출결 사유" in action for action in report.actions)

    one_hard_day = calm[:6] + [("anxious", 3)]
    combined = teacher_report(month(one_hard_day), TODAY, attendance=attendance)
    assert combined.level == "watch" and "출석률 하락과 힘든 날이 함께 나타남" in combined.reasons
    assert teacher_report([rec(0, "sad", 4)], TODAY, attendance=attendance).level == "low_data"


def test_excused_absences_do_not_trigger_attendance_concern():
    from app.attendance import AttendanceDay, attendance_summary

    days = [AttendanceDay(add_days(TODAY, offset), status)
            for offset, status in zip(range(-19, 1), ["present"] * 17 + ["excused", "excused", "late"])]
    summary = attendance_summary(days, TODAY)
    assert summary.recent.rate == 80 and summary.recent.excused == 2 and summary.recent.late == 1
    assert not summary.declining
    assert attendance_summary(days[-4:], TODAY).recent.rate is None


def test_very_hard_days_two_is_watch_three_is_consult():
    two = teacher_report(month([("calm", 3), ("sad", 4), ("calm", 3), ("calm", 3), ("anxious", 5), ("calm", 3), ("calm", 3)]), TODAY)
    assert two.level == "watch" and "많이 힘든 날 2일 (최근 7일)" in two.reasons
    assert any("많이 힘든 날" in a for a in two.actions)
    three = level([("calm", 3), ("sad", 4), ("calm", 3), ("angry", 4), ("calm", 3), ("anxious", 5), ("calm", 3)])
    assert three == "consult"


def test_hard_days_four_is_watch_six_is_consult():
    four = teacher_report(month([("sad", 3), ("calm", 3), ("anxious", 3), ("calm", 3), ("angry", 3), ("calm", 3), ("sad", 3)]), TODAY)
    assert four.level == "watch" and "힘든 날 반복 (7일 중 4일)" in four.reasons
    assert level([("sad", 3), ("anxious", 3), ("angry", 3), ("sad", 3), ("anxious", 3), ("angry", 3), ("calm", 3)]) == "consult"


def test_same_negative_run_counts_only_hard_days():
    r = teacher_report(month([("calm", 3)] * 4 + [("sad", 3)] * 3), TODAY)
    assert r.same_run == (3, "sad") and r.level == "watch"
    mild = teacher_report(month([("calm", 3)] * 4 + [("sad", 2)] * 3), TODAY)
    assert mild.same_run == (0, None) and mild.level == "stable"


def test_old_records_without_intensity_behave_as_before():
    """강도가 없으면 부정 감정을 고른 날이 곧 '힘든 날' (강도를 쓰기 전의 기준과 같음)"""
    assert level([("sad", None), ("calm", None), ("anxious", None), ("calm", None), ("angry", None), ("calm", None), ("sad", None)]) == "watch"
    assert level([("calm", None)] * 5 + [("sad", None), ("calm", None)]) == "stable"
