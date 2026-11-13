"""합성 데이터(data/*.json)와 저장된 상태를 합쳐 화면에 필요한 형태로 꺼내는 함수 모음"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from .analysis import SIGNALS
from .dates import add_days
from .models import Consent, EmotionLog

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


_students_file = _load("students.json")
_agencies_file = _load("agencies.json")
_logs_file = _load("emotion_logs.json")

ME_ID = "S01"  # 학생 모드에서 사용하는 시연용 계정
SCHOOL: str = _students_file["school"]
STUDENTS: list[dict] = _students_file["students"]
AGENCIES: list[dict] = _agencies_file["agencies"]
AGENCY_TYPES: list[dict] = _agencies_file["types"]
REGIONS: list[str] = _agencies_file["regions"]
TOPICS: list[dict] = SIGNALS["topics"]


def get_student(student_id: str) -> dict | None:
    return next((s for s in STUDENTS if s["id"] == student_id), None)


def get_agency(agency_id: str) -> dict | None:
    return next((a for a in AGENCIES if a["id"] == agency_id), None)


def agency_type_label(type_id: str) -> str:
    return next((t["label"] for t in AGENCY_TYPES if t["id"] == type_id), type_id)


def topic_label(topic_id: str) -> str:
    return next((t["label"] for t in TOPICS if t["id"] == topic_id), topic_id)


def seed_logs(student_id: str, today: str) -> list[EmotionLog]:
    """합성 기록의 상대 날짜(day_offset)를 오늘 기준 실제 날짜로 변환"""
    return [
        EmotionLog(
            id=f"{r['student_id']}:{add_days(today, r['day_offset'])}",
            student_id=r["student_id"],
            date=add_days(today, r["day_offset"]),
            emotion=r["emotion"],
            intensity=r["intensity"],
            note=r["note"] or None,
            shared=r["shared"],
        )
        for r in _logs_file["logs"]
        if r["student_id"] == student_id
    ]


def logs_for(student_id: str, state: dict, today: str) -> list[EmotionLog]:
    """한 학생의 전체 기록. 시연용 학생은 직접 남긴 기록과 공유 설정 변경을 반영"""
    base = seed_logs(student_id, today)
    if student_id != ME_ID:
        return base
    by_date = {log.date: log for log in base}
    for raw in state["my_logs"]:
        by_date[raw["date"]] = EmotionLog(**raw)
    overrides = state["share_overrides"]
    logs = [replace(log, shared=overrides[log.id]) if log.id in overrides else log for log in by_date.values()]
    return sorted(logs, key=lambda log: log.date)


def consent_for(student: dict, state: dict) -> Consent:
    return Consent(**(state["consent"] if student["id"] == ME_ID else student["consent"]))


def status_for(student: dict, state: dict) -> str:
    return state["case_status"].get(student["id"], student["case_status"])


def _with_date(row: dict, today: str) -> dict:
    out = {k: v for k, v in row.items() if k != "day_offset"}
    out["date"] = add_days(today, row["day_offset"])
    return out


def requests_for(student_id: str, state: dict, today: str) -> list[dict]:
    seeded = [_with_date(r, today) for r in _students_file["seed_requests"] if r["student_id"] == student_id]
    mine = [r for r in state["requests"] if r["student_id"] == student_id]
    return sorted(seeded + mine, key=lambda r: r["date"], reverse=True)


def referrals_for(student_id: str, state: dict, today: str) -> list[dict]:
    seeded = [_with_date(r, today) for r in _students_file["seed_referrals"] if r["student_id"] == student_id]
    mine = [r for r in state["referrals"] if r["student_id"] == student_id]
    return sorted(seeded + mine, key=lambda r: r["date"], reverse=True)


def match_agencies(
    agencies: list[dict], type_id: str = "all", region: str = "all", student_topics: list[str] | None = None
) -> list[dict]:
    """조건(유형·지역)에 맞는 기관을 고르고, 학생의 고민 주제와 겹치는 기관을 앞에 배치"""
    topics = student_topics or []
    matches = [
        {"agency": a, "matched_topics": [t for t in a["topics"] if t in topics]}
        for a in agencies
        if (type_id == "all" or a["type"] == type_id) and (region == "all" or a["region"] == region)
    ]
    return sorted(matches, key=lambda m: len(m["matched_topics"]), reverse=True)
