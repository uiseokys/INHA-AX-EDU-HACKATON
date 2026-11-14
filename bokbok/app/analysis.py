"""복복복 감정 기록 분석 (규칙 기반 Mock AI)

기획서 (2)-2 의 분석 요소를 규칙으로 계산합니다.
  · 부정적 감정의 발생 빈도            · 동일한 부정적 감정의 지속 기간
  · 평소 감정 패턴과 달라진 정도        · 특정 감정이 반복적으로 나타나는지 여부
  · 감정 변화가 발생한 시점과 추이      · 학생이 작성한 추가 문장의 정서적 특징(키워드)

실제 AI 모델을 붙일 때는 student_report() / teacher_report() 의 내부만 바꾸고,
돌려주는 자료형(StudentReport, TeacherReport)을 유지하면 화면 코드는 그대로 동작합니다.

이 분석은 참고 정보이며, 학교폭력 피해 여부나 정신건강 상태를 진단·판정하지 않습니다.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from .attendance import AttendanceSummary
from .data import SIGNALS, teacher_record
from .dates import add_days, day_label, short_label, week_start
from .models import EMOTIONS, Record

RULES = SIGNALS["rules"]
def _norm(text: str) -> str:
    return "".join(text.split())


def risk_hits(text: str | None) -> list[dict]:
    """문장에서 위험 신호 키워드 찾기 (띄어쓰기 무시). [{id, label, help, matched}]"""
    if not text:
        return []
    t = _norm(text)
    hits = []
    for cat in SIGNALS["risk"]:
        matched = [k for k in cat["keywords"] if _norm(k) in t]
        if matched:
            hits.append({"id": cat["id"], "label": cat["label"], "help": cat["help"], "matched": matched})
    return hits


# 하루 기록 구분: 고른 감정과 강도(1~5)로 나눕니다. 가벼운 부정 감정은 누구에게나 있는 '보통 날'로 봅니다.
DAY_KINDS = {"good": "좋은 날", "ok": "보통 날", "hard": "힘든 날", "very_hard": "많이 힘든 날"}


def day_kind(r: Record) -> str:
    """good(긍정 감정) · ok(부정, 강도 1~2) · hard(부정, 강도 3) · very_hard(부정, 강도 4~5)

    강도가 없는 예전 기록은 '보통'(3)으로 봅니다. 그래서 강도를 쓰기 전의 기준과 결과가 이어집니다.
    """
    if not EMOTIONS[r.emotion].negative:
        return "good"
    n = r.intensity or RULES["default_intensity"]
    if n <= RULES["mild_intensity_max"]:
        return "ok"
    return "very_hard" if n >= RULES["strong_intensity_min"] else "hard"


def is_hard(r: Record) -> bool:
    return day_kind(r) in ("hard", "very_hard")


def mood_score(r: Record) -> float:
    """그날의 마음 점수 1(무거움)~5(가벼움). 감정마다 정해 둔 점수를 쓰되, 가벼운 부정 감정('보통 날')은 가운데 점수로 봅니다.

    이렇게 해야 '조금 걱정되는 날'이 며칠 이어졌다고 평소보다 크게 나빠진 것으로 계산되지 않습니다.
    """
    return RULES["mild_negative_score"] if day_kind(r) == "ok" else EMOTIONS[r.emotion].score


def round1(n: float) -> float:
    return math.floor(n * 10 + 0.5) / 10


def fmt(n: float | None) -> str:
    """3.0 → '3', 3.6 → '3.6'"""
    if n is None:
        return "-"
    s = f"{n:.1f}"
    return s[:-2] if s.endswith(".0") else s


def _mean(xs: list[float]) -> float | None:
    return round1(sum(xs) / len(xs)) if xs else None


@dataclass
class SeriesPoint:
    date: str
    label: str
    score: float | None = None  # 마음 점수 1(무거움)~5(가벼움). 기록이 없는 날은 None
    avg: float | None = None  # 최근 3회 이동평균
    emotion: str | None = None
    words: tuple[str, ...] = ()
    note: str | None = None


def build_series(records: list[Record], today: str, days: int = 14) -> list[SeriesPoint]:
    by_date = {r.date: r for r in records}
    recent: list[float] = []
    out = []
    for i in range(days - 1, -1, -1):
        d = add_days(today, -i)
        r = by_date.get(d)
        if r is None:
            out.append(SeriesPoint(d, short_label(d)))
            continue
        score = mood_score(r)
        recent.append(score)
        out.append(SeriesPoint(d, short_label(d), score, _mean(recent[-RULES["moving_average_window"]:]), r.emotion, r.words, r.note))
    return out


def _in(records: list[Record], start: str, end: str) -> list[Record]:
    return [r for r in records if start <= r.date <= end]


def _top_emotion(records: list[Record]) -> dict | None:
    if not records:
        return None
    emotion, count = Counter(r.emotion for r in records).most_common(1)[0]
    return {"emotion": emotion, "count": count, "pct": round(count / len(records) * 100)}


def ratio(records: list[Record]) -> list[dict]:
    c = Counter(r.emotion for r in records)
    return [
        {"emotion": e, "count": c[e], "pct": round(c[e] / len(records) * 100)}
        for e in sorted(c, key=lambda e: -c[e])
    ] if records else []


def top_words(records: list[Record], n: int = 6) -> list[dict]:
    c = Counter(w for r in records for w in r.words)
    return [{"word": w, "count": k, "negative": _word_negative(w)} for w, k in c.most_common(n)]


def _word_negative(word: str) -> bool:
    return any(word in e.words for e in EMOTIONS.values() if e.negative)


def topics(records: list[Record]) -> list[dict]:
    """부정 감정을 기록한 날의 문장에서 고민 주제 분류. evidence 에는 문장이 아닌 기록 자체가 담깁니다."""
    heavy = [r for r in records if r.note and EMOTIONS[r.emotion].negative]
    out = []
    for t in SIGNALS["topics"]:
        hits = [r for r in heavy if any(k in r.note for k in t["keywords"])]
        if hits:
            out.append({"id": t["id"], "label": t["label"], "emoji": t["emoji"], "count": len(hits), "records": hits})
    return sorted(out, key=lambda t: -t["count"])


def _same_negative_run(records: list[Record], today: str) -> tuple[int, str | None]:
    """가장 최근(오늘·어제)부터 이어지는 '같은 부정 감정' 연속 기록 일수 (강도 1~2의 가벼운 날은 세지 않음)"""
    by_date = {r.date: r for r in records}
    start = today if today in by_date else add_days(today, -1)
    first = by_date.get(start)
    if not first or not is_hard(first):
        return 0, None
    n, d = 0, start
    while d in by_date and by_date[d].emotion == first.emotion and is_hard(by_date[d]):
        n, d = n + 1, add_days(d, -1)
    return n, first.emotion


def _change_day(series: list[SeriesPoint], baseline: float | None) -> SeriesPoint | None:
    """이동평균이 평소보다 기준 이상 낮아지기 시작한 날"""
    if baseline is None:
        return None
    pts = [p for p in series if p.avg is not None]
    return next((p for i, p in enumerate(pts) if i >= 2 and baseline - p.avg >= RULES["baseline_drop_watch"]), None)


# ── 학생용 리포트 ─────────────────────────────────────────────────────────────


@dataclass
class StudentReport:
    enough: bool
    record_count: int
    this_week: list[Record]
    last_week: list[Record]
    top_this_week: dict | None
    top_last_week: dict | None
    week_avg: float | None
    last_week_avg: float | None
    words: list[dict]
    series: list[SeriesPoint]
    ratio: list[dict]
    questions: list[str]
    summary: list[str] = field(default_factory=list)


def student_report(records: list[Record], today: str) -> StudentReport:
    ws = week_start(today)
    this_week = _in(records, ws, today)
    last_week = _in(records, add_days(ws, -7), add_days(ws, -1))
    recent14 = _in(records, add_days(today, -13), today)
    top = _top_emotion(this_week)
    top_last = _top_emotion(last_week)
    avg, last_avg = _mean([mood_score(r) for r in this_week]), _mean([mood_score(r) for r in last_week])

    summary = []
    if top:
        e = EMOTIONS[top["emotion"]]
        summary.append(f"이번 주에는 ‘{e.label}’을 가장 많이 느꼈어요. ({len(this_week)}번 중 {top['count']}번)")
    if avg is not None and last_avg is not None:
        diff = round1(avg - last_avg)
        if diff <= -0.6:
            summary.append("지난주보다 마음이 조금 무거워졌어요. 요즘 나를 힘들게 하는 일이 있는지 돌아봐요.")
        elif diff >= 0.6:
            summary.append("지난주보다 마음이 한결 가벼워졌어요. 무엇이 도움이 됐는지 기억해 두면 좋아요.")
        else:
            summary.append("지난주와 비슷한 마음으로 한 주를 보내고 있어요.")
    words = top_words(recent14, 6)
    if words:
        summary.append(f"최근 2주 동안 ‘{words[0]['word']}’ 마음을 가장 자주 골랐어요.")

    focus = (top or top_last or {"emotion": "calm"})["emotion"]
    return StudentReport(
        enough=len(recent14) >= RULES["min_records"],
        record_count=len(recent14),
        this_week=this_week,
        last_week=last_week,
        top_this_week=top,
        top_last_week=top_last,
        week_avg=avg,
        last_week_avg=last_avg,
        words=words,
        series=build_series(records, today, 14),
        ratio=ratio(recent14),
        questions=SIGNALS["questions"][focus],
        summary=summary,
    )


# ── 교사용 리포트 ─────────────────────────────────────────────────────────────


@dataclass
class Signal:
    date: str
    source: str  # record | chat | pattern
    label: str
    detail: str
    level: str = "issue"  # care(살펴보기) · issue(확인 필요) · urgent(긴급)


@dataclass
class TeacherReport:
    level: str  # consult | watch | low_data | stable
    reasons: list[str]  # 학생별 확인 목록에 보여 줄 짧은 이유
    record_count: int
    series: list[SeriesPoint]
    main: dict | None  # 주요 감정 (최근 14일)
    ratio: list[dict]
    repeated_words: list[dict]
    negative_week: int
    same_run: tuple[int, str | None]
    baseline: float | None
    recent: float | None
    change_day: SeriesPoint | None
    topics: list[dict]
    signals: list[Signal]
    actions: list[str]  # 추가 확인 사항 및 권장 조치
    week_kinds: dict[str, int] = field(default_factory=dict)  # 최근 7일의 하루 구분별 일수 (DAY_KINDS)


def teacher_report(records: list[Record], today: str, alerts: list[dict] | None = None, *,
                   attendance: AttendanceSummary | None = None) -> TeacherReport:
    """전체 기록에서 위험 신호를 확인하고, 교사용 그래프와 주제에는 공유 문장만 사용합니다."""
    recent7 = _in(records, add_days(today, -6), today)
    recent14 = _in(records, add_days(today, -13), today)
    base = _in(records, add_days(today, -34), add_days(today, -8))
    baseline = _mean([mood_score(r) for r in base]) if len(base) >= 5 else None
    recent = _mean([mood_score(r) for r in recent7]) if len(recent7) >= 3 else None
    negative_week = sum(1 for r in recent7 if EMOTIONS[r.emotion].negative)
    week_kinds = {k: sum(1 for r in recent7 if day_kind(r) == k) for k in DAY_KINDS}
    very_hard_week = week_kinds["very_hard"]
    hard_week = week_kinds["hard"] + very_hard_week  # 힘든 날 + 많이 힘든 날
    run, run_emotion = _same_negative_run(records, today)
    public_records = [teacher_record(r) for r in recent14]
    series = build_series(public_records, today, 14)
    drop = round1(baseline - recent) if baseline is not None and recent is not None else None

    signals: list[Signal] = []
    for r in recent14:
        hits = risk_hits(r.note)
        if hits:  # 어떤 표현이었는지(분류·키워드)는 보여 주지 않고, 신호가 있었다는 사실과 단계만 알림
            level = "urgent" if any(h["id"] == "urgent" for h in hits) else "issue"
            signals.append(Signal(r.date, "record", "감정 기록에서 위험 신호가 감지되었어요", "", level))
    for a in alerts or []:
        if a["source"] == "chat" and a["date"] >= add_days(today, -13):
            # 선생님께는 무슨 이야기였는지(분류·요약)를 보여 주지 않고, 신호가 있었다는 사실과 단계만 알림
            level = a.get("level", "issue")
            label = "대화에서 살펴볼 신호가 감지되었어요" if level == "care" else "대화에서 위험 신호가 감지되었어요"
            if not any(s.source == "chat" and s.date == a["date"] and s.level == level for s in signals):
                signals.append(Signal(a["date"], "chat", label, "", level))

    consult, watch, reasons = False, False, []
    if any(s.level != "care" for s in signals):
        consult = True
        reasons.append("위험 신호 감지")
    elif signals:  # 구체적인 피해 없이 마음이 힘들어 보이는 대화만 있을 때
        watch = True
        reasons.append("복복이 대화에서 살펴볼 신호")
    attendance_declining = attendance is not None and attendance.declining
    if attendance_declining and hard_week:
        watch = True
        reasons.append("출석률 하락과 힘든 날이 함께 나타남")
    if (very_hard_week >= RULES["very_hard_week_consult"] or hard_week >= RULES["negative_week_consult"]
            or run >= RULES["same_negative_consult"]):
        consult = True
    elif (very_hard_week >= RULES["very_hard_week_watch"] or hard_week >= RULES["negative_week_watch"]
          or run >= RULES["same_negative_watch"]):
        watch = True
    if very_hard_week >= RULES["very_hard_week_watch"]:
        reasons.append(f"많이 힘든 날 {very_hard_week}일 (최근 7일)")
    if run >= RULES["same_negative_watch"]:
        reasons.append(f"‘{EMOTIONS[run_emotion].label}’ {run}일 연속")
    elif hard_week >= RULES["negative_week_watch"] and hard_week > very_hard_week:  # 위 이유와 같은 날들이면 겹쳐 쓰지 않음
        reasons.append(f"힘든 날 반복 (7일 중 {hard_week}일)")
    if drop is not None and drop >= RULES["baseline_drop_consult"]:
        consult = True
        reasons.append("최근 정서 변화 급증")
    elif drop is not None and drop >= RULES["baseline_drop_watch"]:
        watch = True
        reasons.append("평소보다 마음 점수 하락")

    main = _top_emotion(recent14)
    # 2주 기록의 절반 이상이 같은 부정 감정으로 '힘든 날'일 때 (가벼운 날은 세지 않음)
    same_hard = sum(1 for r in recent14 if main and r.emotion == main["emotion"] and is_hard(r))
    if (main and EMOTIONS[main["emotion"]].negative and len(recent14) >= RULES["min_records"]
            and same_hard * 100 >= RULES["repeat_negative_pct"] * len(recent14)):
        watch = True
        reasons.append(f"‘{EMOTIONS[main['emotion']].label}’ 반복 (2주 중 {same_hard}일)")

    if len(recent14) < RULES["min_records"] and not consult:
        level = "low_data"
        reasons = [f"최근 2주 기록 {len(recent14)}건"]
    else:
        level = "consult" if consult else "watch" if watch else "stable"
    if level == "stable":
        reasons = ["특이 변화 없음"]

    tps = topics(public_records)
    actions = []
    if any(s.level == "urgent" for s in signals):
        actions.append("오늘 안에 학생의 안전을 직접 확인하고, Wee클래스와 함께 대응을 의논해 주세요.")
    elif any(s.level == "issue" for s in signals):
        actions.append("학생과 단둘이 이야기할 시간을 마련해 무슨 일이 있는지 조심스럽게 들어 주세요. 필요하면 Wee클래스와 함께 의논해 주세요.")
    if any(s.level == "care" for s in signals):
        actions.append("복복이 대화에서 살펴볼 신호가 있었어요. 이유를 캐묻기보다 가벼운 안부 대화로 먼저 다가가 주세요.")
    if very_hard_week >= RULES["very_hard_week_watch"]:
        actions.append(f"최근 일주일에 ‘많이 힘든 날’이 {very_hard_week}일 있었어요. 그날 무슨 일이 있었는지 편하게 물어봐 주세요.")
    if run >= RULES["same_negative_watch"]:
        actions.append(f"‘{EMOTIONS[run_emotion].label}’이 계속되고 있어요. 가벼운 안부 대화로 요즘 상황을 물어봐 주세요.")
    if tps:
        actions.append(f"‘{tps[0]['label']}’ 관련 고민이 반복돼요. 면담 때 이 주제를 먼저 꺼내 보세요.")
    if attendance_declining:
        actions.append("최근 출석률이 낮아졌어요. 출결 사유를 먼저 확인하고 학생에게 가볍게 안부를 물어봐 주세요.")
    if level == "low_data":
        actions.append("기록이 적어 흐름을 판단하기 어려워요. 기록을 강요하기보다 안부를 먼저 물어봐 주세요.")
    if not actions:
        actions.append("특별한 조치는 필요해 보이지 않아요. 평소처럼 관심을 가져 주세요.")

    return TeacherReport(
        level=level,
        reasons=reasons[:3],
        record_count=len(recent14),
        series=series,
        main=main,
        ratio=ratio(recent14),
        repeated_words=top_words(recent14, 6),
        negative_week=negative_week,
        same_run=(run, run_emotion),
        baseline=baseline,
        recent=recent,
        change_day=_change_day(series, baseline),
        topics=tps,
        signals=sorted(signals, key=lambda s: s.date, reverse=True),
        actions=actions,
        week_kinds=week_kinds,
    )


def describe_change(report: TeacherReport) -> str:
    if report.baseline is None or report.recent is None:
        return "비교할 기록이 부족해요."
    diff = round1(report.recent - report.baseline)
    word = "낮아" if diff < 0 else "높아"
    if abs(diff) < 0.4:
        return f"평소(마음 점수 {fmt(report.baseline)})와 비슷해요."
    text = f"평소 {fmt(report.baseline)}점 → 최근 7일 {fmt(report.recent)}점으로 {fmt(abs(diff))}점 {word}졌어요."
    if report.change_day and diff <= -RULES["baseline_drop_watch"]:
        text += f" {day_label(report.change_day.date)}부터 달라지기 시작했어요."
    return text
