"""그래프를 서버에서 그리기 위한 좌표 계산 (별도 차트 라이브러리 없이 SVG + HTML로 렌더링)

좌표는 모두 0~100의 백분율입니다. 템플릿에서 선은 SVG로, 점과 눈금은 백분율 위치의 HTML 요소로 그려
화면 크기에 맞게 늘어나도 글자와 선 굵기가 일정하게 유지됩니다.
"""

from __future__ import annotations

from .analysis import SeriesPoint
from .assessments import Assessment
from .attendance import STATUS_LABELS, AttendanceSummary
from .models import EMOTIONS


def _smooth_path(pts: list[tuple[float, float]]) -> str:
    """점들을 부드럽게 잇되 값이 튀지 않는 곡선(단조 3차 보간)"""
    n = len(pts)
    if n == 0:
        return ""
    path = f"M {pts[0][0]:.2f} {pts[0][1]:.2f}"
    if n == 1:
        return path
    dx = [pts[i + 1][0] - pts[i][0] for i in range(n - 1)]
    slope = [(pts[i + 1][1] - pts[i][1]) / dx[i] for i in range(n - 1)]
    tangent = [slope[0]]
    for i in range(1, n - 1):
        if slope[i - 1] * slope[i] <= 0:
            tangent.append(0.0)
        else:
            w1, w2 = 2 * dx[i] + dx[i - 1], dx[i] + 2 * dx[i - 1]
            tangent.append((w1 + w2) / (w1 / slope[i - 1] + w2 / slope[i]))
    tangent.append(slope[-1])
    for i in range(n - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        h = dx[i] / 3
        path += f" C {x0 + h:.2f} {y0 + tangent[i] * h:.2f}, {x1 - h:.2f} {y1 - tangent[i + 1] * h:.2f}, {x1:.2f} {y1:.2f}"
    return path


def mood_chart(series: list[SeriesPoint], today: str, *, attendance: AttendanceSummary | None = None,
               assessments: list[Assessment] | None = None) -> dict:
    """마음 점수와 출석률, 평가 일정을 같은 날짜 위치에 배치합니다."""
    n = len(series)

    def x(i: int) -> float:
        return 100 * i / max(n - 1, 1)

    def y(score: float) -> float:
        return 100 * (5 - score) / 4  # 5점이 맨 위(0%), 1점이 맨 아래(100%)

    recorded = [(i, p) for i, p in enumerate(series) if p.score is not None]
    score_pts = [(x(i), y(p.score)) for i, p in recorded]
    avg_pts = [(x(i), y(p.avg)) for i, p in recorded]
    score_path = _smooth_path(score_pts)
    area_path = ""
    if len(score_pts) >= 2:
        area_path = f"{score_path} L {score_pts[-1][0]:.2f} 100 L {score_pts[0][0]:.2f} 100 Z"

    rates = attendance.rolling_rates() if attendance else {}
    statuses = {d.date: STATUS_LABELS[d.status] for d in attendance.recent.days + attendance.previous.days} if attendance else {}
    attendance_dots = []
    for i, p in enumerate(series):
        if p.date in rates:
            rate = rates[p.date]
            attendance_dots.append({"date": p.date, "rate": rate, "status": statuses[p.date], "x": round(x(i), 2),
                                    "y": 100 - rate, "align": "left" if x(i) < 30 else "right" if x(i) > 70 else "center"})

    evaluation_dates = {}
    for assessment in assessments or []:
        title = f"{assessment.subject} {assessment.kind}"
        score = assessment.score if assessment.result_date <= today else None
        if assessment.exam_date <= today:
            evaluation_dates.setdefault(assessment.exam_date, []).append({"label": f"시험일 · {title}", "score": score})
        if assessment.result_date <= today:
            evaluation_dates.setdefault(assessment.result_date, []).append({"label": f"결과 공개 · {title}", "score": score})

    return {
        "score_path": score_path if len(score_pts) >= 2 else "",
        "avg_path": _smooth_path(avg_pts) if len(avg_pts) >= 2 else "",
        "area_path": area_path,
        "attendance_dots": attendance_dots,
        "attendance_path": " ".join(f"{d['x']},{d['y']}" for d in attendance_dots),
        "assessment_marks": [
            {"date": p.date, "x": round(x(i), 2), "events": evaluation_dates[p.date],
             "align": "left" if x(i) < 30 else "right" if x(i) > 70 else "center"}
            for i, p in enumerate(series) if p.date in evaluation_dates
        ],
        "dots": [
            {
                "x": round(x(i), 2),
                "y": round(y(p.score), 2),
                "point": p,
                "today": p.date == today,
                "align": "left" if x(i) < 30 else "right" if x(i) > 70 else "center",
                "below": y(p.score) < 35,  # 위쪽 점은 설명을 아래로 펼침
            }
            for i, p in recorded
        ],
        "ticks": [{"x": round(x(i), 2), "label": p.label} for i, p in enumerate(series) if (n - 1 - i) % 2 == 0],
        "grid": [{"y": y(v), "label": v} for v in (5, 4, 3, 2, 1)],
    }


def donut(ratio: list[dict]) -> list[dict]:
    """감정별 기록 비율 도넛 조각 (둘레를 100으로 본 길이와 시작 위치)"""
    total = sum(r["count"] for r in ratio)
    gap = 1.2 if len(ratio) > 1 else 0
    segments, start = [], 0.0
    for r in ratio:
        length = r["count"] / total * 100
        segments.append({"color": EMOTIONS[r["emotion"]].color, "len": round(max(length - gap, 0.5), 2), "start": round(start, 2)})
        start += length
    return segments


def sparkline(series: list[SeriesPoint], width: int = 96, height: int = 32) -> dict | None:
    """목록용 작은 추이선. 기록이 2건 미만이면 None"""
    n = len(series)
    pts = [
        ((i / (n - 1)) * (width - 6) + 3, height - 4 - ((p.score - 1) / 4) * (height - 8))
        for i, p in enumerate(series)
        if p.score is not None
    ]
    if len(pts) < 2:
        return None
    return {
        "width": width,
        "height": height,
        "points": " ".join(f"{px:.1f},{py:.1f}" for px, py in pts),
        "last": {"x": round(pts[-1][0], 1), "y": round(pts[-1][1], 1)},
    }
