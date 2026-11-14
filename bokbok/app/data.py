"""합성 데이터(data/*.json)와 저장된 상태를 합쳐 화면에 필요한 형태로 꺼내는 함수 모음"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from .assessments import Assessment
from .attendance import WINDOW, AttendanceDay, AttendanceStatus
from .dates import add_days
from .models import Record

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


_class = _load("class.json")
_records = _load("records.json")["records"]
_attendance: dict[str, dict[AttendanceStatus, list[int]]] = _load("attendance.json")["students"]
_assessments = _load("assessments.json")["students"]
SIGNALS = _load("signals.json")
HELP = _load("help.json")
CHATBOT = _load("chatbot.json")

ME_ID = "S01"  # 학생 모드에서 사용하는 시연용 계정
SCHOOL: str = _class["school"]
CLASS_NAME: str = _class["class_name"]
TEACHERS: dict[str, dict] = _class["teachers"]
STUDENTS: list[dict] = _class["students"]
CONTACTS: dict[str, dict] = {c["id"]: c for c in HELP["contacts"]}
HELP_CATEGORIES: list[dict] = HELP["categories"]
HELP_LINKS: list[dict] = HELP["links"]


def get_student(student_id: str) -> dict | None:
    return next((s for s in STUDENTS if s["id"] == student_id), None)


def get_help(slug: str) -> dict | None:
    return next((c for c in HELP_CATEGORIES if c["id"] == slug), None)


def seed_records(student_id: str, today: str) -> list[Record]:
    """합성 기록의 상대 날짜(day_offset)를 오늘 기준 실제 날짜로 변환"""
    return [
        Record(
            id=f"{r['student_id']}:{add_days(today, r['day_offset'])}",
            student_id=r["student_id"],
            date=add_days(today, r["day_offset"]),
            emotion=r["emotion"],
            words=tuple(r["words"]),
            note=r["note"] or None,
            shared=r["shared"],
            intensity=r.get("intensity"),
        )
        for r in _records
        if r["student_id"] == student_id
    ]


def records_for(student_id: str, state: dict, today: str) -> list[Record]:
    """한 학생의 전체 기록(날짜순). 시연용 학생은 직접 남긴 기록과 공유 설정 변경을 반영"""
    base = seed_records(student_id, today)
    if student_id == ME_ID:
        by_date = {r.date: r for r in base}
        for raw in state["my_records"]:
            by_date[raw["date"]] = Record(**{**raw, "words": tuple(raw["words"])})
        overrides = state["share_overrides"]
        base = [replace(r, shared=overrides[r.id]) if r.id in overrides else r for r in by_date.values()]
    return sorted((r for r in base if r.date <= today), key=lambda r: r.date)


def attendance_for(student_id: str, today: str) -> list[AttendanceDay]:
    """시연 기준일 전에 종료된 평일 수업일을 출결 원본으로 펼칩니다."""
    if student_id not in _attendance:
        return []
    statuses = {offset: status for status, offsets in _attendance[student_id].items() for offset in offsets}
    day = date.fromisoformat(today) - timedelta(days=1)
    days = []
    while len(days) < 2 * WINDOW:
        if day.weekday() < 5:
            days.append(AttendanceDay(day.isoformat(), statuses.get(-len(days), "present")))
        day -= timedelta(days=1)
    return days[::-1]


def assessments_for(student_id: str, today: str) -> list[Assessment]:
    return [Assessment(r["subject"], r["kind"], add_days(today, r["exam_offset"]),
                       add_days(today, r["result_offset"]), r["score"])
            for r in _assessments.get(student_id, [])]


def school_schedule_for(student_id: str, today: str) -> dict[str, list[str]]:
    events = defaultdict(list)
    for event in _class.get("school_schedule", []):
        events[event["date"]].append(event["title"])
    for assessment in assessments_for(student_id, today):
        title = f"{assessment.subject} {assessment.kind}"
        events[assessment.exam_date].append(title)
        events[assessment.result_date].append(f"{title} 결과 공개")
    return events


def profile_for(student: dict, state: dict) -> dict | None:
    return state["profile"] if student["id"] == ME_ID else student["profile"]


def teacher_record(record: Record) -> Record:
    """교사 화면용 기록: 학생이 공유하지 않은 문장은 지움"""
    return record if record.shared else replace(record, note=None)
