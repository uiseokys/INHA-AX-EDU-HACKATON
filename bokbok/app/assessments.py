"""교사 화면에서 평가 결과와 학생이 기록한 감정을 시간순으로 비교합니다."""

from collections import Counter
from dataclasses import dataclass

from .dates import add_days
from .models import EMOTIONS, Record

COMPARISON_DAYS = 7
MIN_RECORDS_PER_WINDOW = 3


@dataclass(frozen=True)
class Assessment:
    subject: str
    kind: str
    exam_date: str
    result_date: str
    score: int


@dataclass(frozen=True)
class EmotionChange:
    emotion: str
    before_count: int
    before_total: int
    after_count: int
    after_total: int


@dataclass(frozen=True)
class AssessmentComparison:
    assessment: Assessment
    previous: Assessment | None
    emotion_change: EmotionChange | None


def _emotion_change(records: list[Record], result_date: str, today: str) -> EmotionChange | None:
    start = add_days(result_date, -COMPARISON_DAYS)
    end = add_days(result_date, COMPARISON_DAYS - 1)
    if end > today:
        return None
    before = Counter(r.emotion for r in records if start <= r.date < result_date)
    after = Counter(r.emotion for r in records if result_date <= r.date <= end)
    before_total, after_total = sum(before.values()), sum(after.values())
    if min(before_total, after_total) < MIN_RECORDS_PER_WINDOW:
        return None

    increases = {
        emotion: after[emotion] / after_total - before[emotion] / before_total
        for emotion, definition in EMOTIONS.items()
        if definition.negative and after[emotion] > before[emotion]
    }
    emotion = max(increases, key=increases.get, default=None)
    if emotion is None or increases[emotion] <= 0:
        return None
    return EmotionChange(emotion, before[emotion], before_total, after[emotion], after_total)


def compare_results(assessments: list[Assessment], records: list[Record], today: str) -> list[AssessmentComparison]:
    published = sorted((a for a in assessments if a.result_date <= today),
                       key=lambda a: (a.exam_date, a.result_date), reverse=True)
    comparisons = []
    for result in published:
        previous = next((a for a in published if a.subject == result.subject and a.kind == result.kind
                         and a.exam_date < result.exam_date and a.result_date < result.result_date), None)
        comparisons.append(AssessmentComparison(result, previous, _emotion_change(records, result.result_date, today)))
    return comparisons
