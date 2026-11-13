"""쓰담 감정 기록 분석 (규칙 기반 Mock AI)

실제 AI 모델을 붙일 때는 이 파일의 `analyze()`만 교체하면 됩니다.
입력(list[EmotionLog])과 출력(Insight) 형태를 유지하면 화면 코드는 그대로 동작합니다.

이 분석은 학생의 자기 이해를 돕는 참고 정보이며,
학교폭력 피해 여부나 정신건강 상태를 진단·판정하지 않습니다.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from .dates import add_days, day_label, short_label
from .models import EMOTIONS, EmotionLog

SIGNALS = json.loads((Path(__file__).resolve().parent.parent / "data" / "signals.json").read_text(encoding="utf-8"))
RULES = SIGNALS["rules"]


@dataclass
class SeriesPoint:
    date: str
    label: str
    score: float | None = None  # 마음 점수 1(무거움)~5(가벼움). 기록이 없는 날은 None
    avg: float | None = None  # 최근 기록 3건 이동평균
    emotion: str | None = None
    intensity: int | None = None
    note: str | None = None


@dataclass
class TopicEvidence:
    date: str
    emotion: str
    note: str
    matched: list[str]


@dataclass
class TopicResult:
    id: str
    label: str
    emoji: str
    count: int
    evidence: list[TopicEvidence]


@dataclass
class ChangePoint:
    date: str
    kind: str  # "shift": 이동평균이 이전 기간 평균과 벌어지기 시작 / "jump": 직전 기록 대비 큰 변화
    delta: float
    description: str
    emotion: str
    intensity: int
    note: str | None


@dataclass
class Change:
    prev_avg: float | None = None
    recent_avg: float | None = None
    diff: float | None = None
    direction: str = "unknown"  # up | down | steady | unknown


@dataclass
class Insight:
    days: int
    record_count: int
    min_records: int
    enough: bool  # 분석에 필요한 최소 기록 수를 채웠는지
    series: list[SeriesPoint]
    ratio: list[dict]  # [{"emotion", "count", "pct"}]
    change: Change
    topics: list[TopicResult] = field(default_factory=list)
    change_points: list[ChangePoint] = field(default_factory=list)


def round1(n: float) -> float:
    return math.floor(n * 10 + 0.5) / 10


def fmt(n: float | None) -> str:
    """3.0 → '3', 3.6 → '3.6'"""
    if n is None:
        return "-"
    s = f"{n:.1f}"
    return s[:-2] if s.endswith(".0") else s


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def mood_score(emotion: str, intensity: int) -> float:
    """감정 종류와 강도를 1~5점의 '마음 점수'로 환산 (3 = 보통)"""
    raw = 3 + EMOTIONS[emotion].valence * intensity * 0.4
    return round1(min(5.0, max(1.0, raw)))


def build_series(logs: list[EmotionLog], today: str, days: int = 14) -> list[SeriesPoint]:
    """최근 N일을 하루 단위로 펼친 그래프용 데이터 (+ 이동평균)"""
    by_date = {log.date: log for log in logs}
    recent: list[float] = []
    out: list[SeriesPoint] = []
    for i in range(days - 1, -1, -1):
        date = add_days(today, -i)
        log = by_date.get(date)
        if log is None:
            out.append(SeriesPoint(date=date, label=short_label(date)))
            continue
        score = mood_score(log.emotion, log.intensity)
        recent.append(score)
        out.append(
            SeriesPoint(
                date=date,
                label=short_label(date),
                score=score,
                avg=round1(_mean(recent[-RULES["moving_average_window"] :])),
                emotion=log.emotion,
                intensity=log.intensity,
                note=log.note,
            )
        )
    return out


def extract_topics(logs: list[EmotionLog]) -> list[TopicResult]:
    """마음이 무거웠던 날의 메모에서 키워드로 고민 주제를 분류"""
    heavy = [log for log in logs if log.note and EMOTIONS[log.emotion].valence <= 0]
    results: list[TopicResult] = []
    for topic in SIGNALS["topics"]:
        evidence = [
            TopicEvidence(log.date, log.emotion, log.note, matched)
            for log in heavy
            if (matched := [k for k in topic["keywords"] if k in log.note])
        ]
        if evidence:
            evidence.sort(key=lambda e: e.date, reverse=True)
            results.append(TopicResult(topic["id"], topic["label"], topic["emoji"], len(evidence), evidence))
    results.sort(key=lambda t: t.count, reverse=True)
    return results


def analyze(all_logs: list[EmotionLog], today: str, days: int = 14) -> Insight:
    start = add_days(today, -(days - 1))
    logs = sorted((log for log in all_logs if start <= log.date <= today), key=lambda log: log.date)

    series = build_series(logs, today, days)
    points = [p for p in series if p.score is not None]

    # 1) 감정별 기록 비율
    ratio = []
    for emotion in EMOTIONS:
        count = sum(1 for log in logs if log.emotion == emotion)
        if count:
            ratio.append({"emotion": emotion, "count": count, "pct": math.floor(count / len(logs) * 100 + 0.5)})
    ratio.sort(key=lambda r: r["count"], reverse=True)

    # 2) 이전 기간 vs 최근 기간 평균 비교
    recent_start = add_days(today, -(RULES["period_days"] - 1))
    prev = [p.score for p in points if p.date < recent_start]
    recent = [p.score for p in points if p.date >= recent_start]
    prev_avg = round1(_mean(prev)) if len(prev) >= 2 else None
    recent_avg = round1(_mean(recent)) if len(recent) >= 2 else None
    diff = round1(recent_avg - prev_avg) if prev_avg is not None and recent_avg is not None else None
    if diff is None:
        direction = "unknown"
    elif diff <= -RULES["change_threshold"]:
        direction = "down"
    elif diff >= RULES["change_threshold"]:
        direction = "up"
    else:
        direction = "steady"

    # 3) 변화가 나타난 날짜와 그날의 기록
    change_points: list[ChangePoint] = []
    if prev_avg is not None and direction in ("down", "up"):
        sign = -1 if direction == "down" else 1
        shift = next(
            (p for i, p in enumerate(points) if i >= 2 and (p.avg - prev_avg) * sign >= RULES["change_threshold"]),
            None,
        )
        if shift:
            gap = round1(shift.avg - prev_avg)
            change_points.append(
                ChangePoint(
                    date=shift.date,
                    kind="shift",
                    delta=gap,
                    description=(
                        f"최근 기록 3건의 평균({fmt(shift.avg)}점)이 이전 기간 평균({fmt(prev_avg)}점)과 "
                        f"{fmt(abs(gap))}점 벌어지기 시작한 날"
                    ),
                    emotion=shift.emotion,
                    intensity=shift.intensity,
                    note=shift.note,
                )
            )
    jumps = [
        (points[i], round1(points[i].score - points[i - 1].score), points[i - 1])
        for i in range(1, len(points))
    ]
    jumps = [j for j in jumps if abs(j[1]) >= RULES["jump_threshold"]]
    jumps.sort(key=lambda j: abs(j[1]), reverse=True)
    for point, delta, before in jumps[:2]:
        if any(c.date == point.date for c in change_points):
            continue
        change_points.append(
            ChangePoint(
                date=point.date,
                kind="jump",
                delta=delta,
                description=(
                    f"직전 기록({day_label(before.date)}, {fmt(before.score)}점)보다 "
                    f"{fmt(abs(delta))}점 {'낮아진' if delta < 0 else '높아진'} 날"
                ),
                emotion=point.emotion,
                intensity=point.intensity,
                note=point.note,
            )
        )
    change_points.sort(key=lambda c: c.date)

    return Insight(
        days=days,
        record_count=len(logs),
        min_records=RULES["min_records_for_analysis"],
        enough=len(logs) >= RULES["min_records_for_analysis"],
        series=series,
        ratio=ratio,
        change=Change(prev_avg, recent_avg, diff, direction),
        topics=extract_topics(logs),
        change_points=change_points,
    )


def summarize(insight: Insight, tone: str) -> list[str]:
    """분석 결과를 문장으로 정리. tone: 'student'(친근) / 'teacher'(업무)"""
    s = tone == "student"
    if not insight.enough:
        return [
            f"최근 {insight.days}일 동안 기록이 {insight.record_count}건이라 아직 흐름을 읽기 어려워요. "
            f"{insight.min_records}건 이상 모이면 변화를 정리해 드릴게요."
            if s
            else f"최근 {insight.days}일간 확인 가능한 기록이 {insight.record_count}건으로, "
            f"변화 흐름을 해석하기에 부족합니다(기준 {insight.min_records}건)."
        ]

    lines: list[str] = []
    c = insight.change
    prev_avg, recent_avg = fmt(c.prev_avg), fmt(c.recent_avg)
    if c.direction == "unknown":
        lines.append(
            "기록이 한쪽 기간에 몰려 있어서 이전과 최근을 비교하기는 아직 어려워요."
            if s
            else "기록이 한쪽 기간에 몰려 있어 이전·최근 기간 비교는 어렵습니다."
        )
    elif c.direction == "steady":
        lines.append(
            f"최근 7일 평균 마음 점수는 {recent_avg}점으로, 그 전 7일({prev_avg}점)과 비슷하게 유지되고 있어요."
            if s
            else f"최근 7일 평균 {recent_avg}점, 이전 7일 평균 {prev_avg}점으로 큰 변화는 보이지 않습니다."
        )
    else:
        word = "낮아" if c.direction == "down" else "높아"
        gap = fmt(abs(c.diff))
        lines.append(
            f"최근 7일 평균 마음 점수는 {recent_avg}점으로, 그 전 7일({prev_avg}점)보다 {gap}점 {word}졌어요."
            if s
            else f"최근 7일 평균 {recent_avg}점으로 이전 7일({prev_avg}점) 대비 {gap}점 {word}졌습니다."
        )

    if insight.topics:
        top = insight.topics[0]
        lines.append(
            f"마음이 무거웠던 날의 기록에서 '{top.label}'와 관련된 표현이 {top.count}번 나왔어요."
            if s
            else f"공유된 기록 중 '{top.label}' 관련 표현이 {top.count}건 반복됩니다."
        )

    shift = next((p for p in insight.change_points if p.kind == "shift"), None)
    if shift:
        lines.append(
            f"{day_label(shift.date)}부터 흐름이 달라지기 시작한 것으로 보여요."
            if s
            else f"{day_label(shift.date)}부터 변화가 나타나기 시작한 것으로 보입니다."
        )

    if insight.ratio and c.direction != "down":
        main = insight.ratio[0]
        e = EMOTIONS[main["emotion"]]
        lines.append(
            f"가장 자주 고른 감정은 {e.emoji} '{e.label}'({main['pct']}%)예요."
            if s
            else f"가장 많이 기록된 감정은 '{e.label}'({main['pct']}%)입니다."
        )
    return lines
