"""포인트 계산 (기획서 (5)-1)

포인트는 감정 기록 '참여'에 대한 보상으로만 지급합니다. 긍정/부정 감정에 따라 더하거나 빼지 않습니다.
적립 내역은 감정 기록에서 매번 다시 계산하므로 따로 저장하지 않습니다.
"""

from __future__ import annotations

from dataclasses import dataclass

from .dates import add_days
from .models import Record

DAILY = 10  # 하루 감정 기록 완료
NOTE = 5  # 감정에 대한 추가 설명 작성
WEEK_STREAK = 20  # 일주일 연속 감정 기록 (7일마다)
MONTH = 50  # 한 달간 꾸준히 기록 (같은 달 20일째 기록)
MONTH_GOAL = 20
NOTE_MIN = 5  # 추가 설명으로 인정하는 최소 글자 수


@dataclass
class Entry:
    date: str
    label: str
    amount: int
    kind: str  # earn | spend | hold


def earned(records: list[Record]) -> list[Entry]:
    entries: list[Entry] = []
    dates = {r.date for r in records}
    month_count: dict[str, int] = {}
    for r in sorted(records, key=lambda r: r.date):
        entries.append(Entry(r.date, "하루 감정 기록 완료", DAILY, "earn"))
        if r.note and len(r.note.strip()) >= NOTE_MIN:
            entries.append(Entry(r.date, "감정에 대한 추가 설명 작성", NOTE, "earn"))
        streak, d = 0, r.date
        while d in dates:
            streak, d = streak + 1, add_days(d, -1)
        if streak % 7 == 0:
            entries.append(Entry(r.date, f"{streak}일 연속 감정 기록", WEEK_STREAK, "earn"))
        month = r.date[:7]
        month_count[month] = month_count.get(month, 0) + 1
        if month_count[month] == MONTH_GOAL:
            entries.append(Entry(r.date, f"{int(month[5:])}월 꾸준히 기록 ({MONTH_GOAL}일 달성)", MONTH, "earn"))
    return entries


def ledger(records: list[Record], orders: list[dict], items: dict[str, dict]) -> list[Entry]:
    """적립 + 상점 사용(승인) + 교환 대기(포인트 묶어 둠). 최신순"""
    entries = earned(records)
    for o in orders:
        item = items.get(o["item_id"])
        if not item:
            continue
        if o["status"] == "approved":
            entries.append(Entry(o["date"], f"{item['name']} 교환", -item["price"], "spend"))
        elif o["status"] == "pending":
            entries.append(Entry(o["date"], f"{item['name']} 교환 신청 (승인 대기)", -item["price"], "hold"))
    return sorted(entries, key=lambda e: e.date, reverse=True)


def balance(entries: list[Entry]) -> int:
    """쓸 수 있는 포인트 (승인 대기 중인 교환 금액은 미리 뺌)"""
    return sum(e.amount for e in entries)


def total_earned(entries: list[Entry]) -> int:
    return sum(e.amount for e in entries if e.kind == "earn")


def earned_on(records: list[Record], day: str) -> list[Entry]:
    """그날 새로 받은 포인트 (기록 직후 애니메이션용)"""
    return [e for e in earned(records) if e.date == day]


def streak(records: list[Record], today: str) -> int:
    dates = {r.date for r in records}
    d = today if today in dates else add_days(today, -1)
    n = 0
    while d in dates:
        n, d = n + 1, add_days(d, -1)
    return n
