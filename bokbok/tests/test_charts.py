from app.analysis import SeriesPoint
from app.assessments import Assessment
from app.attendance import AttendanceDay, attendance_summary
from app.charts import mood_chart
from app.dates import add_days


def test_chart_aligns_rolling_attendance_to_emotion_dates():
    today = "2026-11-16"
    history = [AttendanceDay(add_days(today, offset), "present") for offset in range(-14, -4)]
    history += [AttendanceDay("2026-11-12", "late"), AttendanceDay("2026-11-13", "absent"),
                AttendanceDay("2026-11-16", "excused")]
    series = [SeriesPoint(add_days(today, offset), str(offset)) for offset in range(-5, 1)]
    series[2].score = series[2].avg = 2.0  # 결석 기록이 있는 금요일
    chart = mood_chart(series, today, attendance=attendance_summary(history, today))

    marks = {point["date"]: point for point in chart["attendance_dots"]}
    assert marks["2026-11-12"]["rate"] == 100
    assert marks["2026-11-13"]["rate"] == 90
    assert marks["2026-11-16"]["rate"] == 80
    assert marks["2026-11-13"]["x"] == chart["dots"][0]["x"]
    assert "2026-11-14" not in marks and "2026-11-15" not in marks


def test_chart_has_no_attendance_points_before_ten_school_days():
    today = "2026-11-16"
    series = [SeriesPoint("2026-11-13", "11/13"), SeriesPoint(today, "11/16")]
    attendance = attendance_summary([AttendanceDay("2026-11-13", "present")], today)
    assert not mood_chart(series, today, attendance=attendance)["attendance_dots"]


def test_chart_groups_same_day_assessments_and_hides_unpublished_scores():
    today = "2026-11-16"
    series = [SeriesPoint("2026-11-15", "11/15", 2, 2, "sad"), SeriesPoint(today, "11/16")]
    assessments = [Assessment("수학", "단원평가", "2026-11-15", today, 0),
                   Assessment("과학", "수행평가", today, "2026-11-17", 93)]
    chart = mood_chart(series, today, assessments=assessments)
    exam, result = chart["assessment_marks"]
    assert exam["x"] == chart["dots"][0]["x"]
    assert result["events"] == [{"label": "결과 공개 · 수학 단원평가", "score": 0},
                                {"label": "시험일 · 과학 수행평가", "score": None}]
