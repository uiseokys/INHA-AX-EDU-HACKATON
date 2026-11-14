from app.assessments import Assessment, compare_results
from app.models import Record


def test_compares_only_a_previous_published_result_for_the_same_subject_and_type():
    current = Assessment("수학", "단원평가", "2026-11-03", "2026-11-06", 71)
    previous = Assessment("수학", "단원평가", "2026-10-19", "2026-10-22", 82)
    unrelated = [
        Assessment("영어", "단원평가", "2026-10-28", "2026-10-30", 99),
        Assessment("수학", "수행평가", "2026-10-29", "2026-11-02", 97),
        Assessment("수학", "단원평가", "2026-10-30", "2026-11-07", 91),
    ]
    results = compare_results([current, previous, *unrelated], [], "2026-11-06")
    result = next(result for result in results if result.assessment == current)
    assert result.previous == previous and result.emotion_change is None
    assert not any(result.assessment.score == 91 for result in results)


def test_compares_equal_windows_with_enough_emotion_records():
    assessment = Assessment("수학", "단원평가", "2026-11-03", "2026-11-06", 71)

    def record(date, emotion):
        return Record(date, "S04", date, emotion)

    records = [record("2026-10-30", "calm"), record("2026-11-02", "calm"), record("2026-11-05", "calm"),
               record("2026-11-06", "anxious"), record("2026-11-08", "calm"), record("2026-11-12", "anxious"),
               record("2026-11-13", "angry")]
    summary, = compare_results([assessment], records, "2026-11-12")
    change = summary.emotion_change
    assert (change.emotion, change.before_count, change.before_total, change.after_count, change.after_total) == (
        "anxious", 0, 3, 2, 3,
    )
    earlier, = compare_results([assessment], records, "2026-11-11")
    assert earlier.emotion_change is None  # 공개일을 포함한 7일이 지나야 비교
    sparse, = compare_results([assessment], records[:5], "2026-11-12")
    assert sparse.emotion_change is None
