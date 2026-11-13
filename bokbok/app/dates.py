"""날짜 도우미. 날짜는 모두 'YYYY-MM-DD' 문자열로 다루며, 문자열 비교로 선후를 판단할 수 있습니다."""

import os
from datetime import date, timedelta

_WEEK = "월화수목금토일"  # date.weekday(): 월요일 = 0


def today_key() -> str:
    """오늘 날짜(서버 기준). 테스트·시연 때는 환경변수 BOKBOK_TODAY 로 고정할 수 있습니다."""
    return os.environ.get("BOKBOK_TODAY") or date.today().isoformat()


def add_days(key: str, n: int) -> str:
    return (date.fromisoformat(key) + timedelta(days=n)).isoformat()


def diff_days(a: str, b: str) -> int:
    return (date.fromisoformat(a) - date.fromisoformat(b)).days


def short_label(key: str) -> str:
    d = date.fromisoformat(key)
    return f"{d.month}/{d.day}"


def weekday(key: str) -> str:
    return _WEEK[date.fromisoformat(key).weekday()]


def day_label(key: str) -> str:
    return f"{short_label(key)}({weekday(key)})"


def full_label(key: str) -> str:
    d = date.fromisoformat(key)
    return f"{d.month}월 {d.day}일 {weekday(key)}요일"


def relative_label(key: str, today: str) -> str:
    n = diff_days(today, key)
    if n == 0:
        return "오늘"
    if n == 1:
        return "어제"
    if n > 1:
        return f"{n}일 전"
    return day_label(key)


def week_start(key: str) -> str:
    """그 날짜가 속한 주의 월요일"""
    return add_days(key, -date.fromisoformat(key).weekday())


def month_days(key: str) -> list[str | None]:
    """달력용: 그 달의 날짜를 일요일 시작 7칸 단위로 채운 목록 (빈칸은 None)"""
    d = date.fromisoformat(key)
    first = d.replace(day=1)
    nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    lead = (first.weekday() + 1) % 7  # 일요일 = 0
    cells: list[str | None] = [None] * lead
    cells += [(first + timedelta(days=i)).isoformat() for i in range((nxt - first).days)]
    cells += [None] * (-len(cells) % 7)
    return cells
