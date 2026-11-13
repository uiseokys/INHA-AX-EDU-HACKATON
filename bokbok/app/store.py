"""시연용 상태 저장소 (로컬 JSON 파일)

학생 화면과 교사 화면이 같은 파일을 읽기 때문에, 학생이 남긴 기록·신청이 교사 화면에 나타납니다.
⚠️ 시연용 구현입니다. 로그인·암호화·접근 제어 등 민감정보 보호 기능은 구현되어 있지 않고,
   접속한 모든 사람이 하나의 상태를 함께 씁니다.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path

from .dates import add_days, today_key

_LOCK = threading.Lock()
BASE = Path(__file__).resolve().parent.parent


def state_path() -> Path:
    return Path(os.environ.get("BOKBOK_STATE", BASE / "var" / "state.json"))


def upload_dir() -> Path:
    path = Path(os.environ.get("BOKBOK_UPLOADS", BASE / "var" / "uploads"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def initial_state(today: str) -> dict:
    """합성 데이터(data/class.json)의 초기값을 오늘 날짜 기준으로 펼친 상태"""
    seed = json.loads((BASE / "data" / "class.json").read_text(encoding="utf-8"))["seed"]

    def day(offset: int) -> str:
        return add_days(today, offset)

    return {
        "version": 1,
        "profile": None,  # 시연용 학생(하늘)의 기본정보. None 이면 처음 접속 화면을 보여 줌
        "profile_skipped": False,
        "my_records": [],  # 시연용 학생이 직접 남긴 감정 기록
        "share_overrides": {},  # 기록 id → 선생님께 문장 보여 주기 여부
        "chats": [],  # 시연용 학생과 복복이의 대화
        "alerts": [
            {**{k: v for k, v in a.items() if k != "day_offset"}, "date": day(a["day_offset"]), "time": "16:40", "read": False}
            for a in seed["alerts"]
        ],
        "followups": dict(seed["followups"]),
        "followup_notes": {},
        "slots": {
            teacher: [{"id": f"SL-{teacher}-{i}", "date": day(off), "time": time} for i, (off, time) in enumerate(slots)]
            for teacher, slots in seed["slots"].items()
        },
        "bookings": [
            {"id": b["id"], "student_id": b["student_id"], "teacher": b["teacher"], "date": day(b["slot"][0]),
             "time": b["slot"][1], "topic": b["topic"], "status": b["status"], "created": day(-1)}
            for b in seed["bookings"]
        ],
        "items": [{**item, "image": None, "start": None, "end": None} for item in seed["items"]],
        "orders": [
            {**{k: v for k, v in o.items() if k != "day_offset"}, "date": day(o["day_offset"])} for o in seed["orders"]
        ],
    }


def load() -> dict:
    """저장된 상태를 읽습니다. 파일이 없거나 깨졌으면 초기 상태를 돌려줍니다."""
    initial = initial_state(today_key())
    try:
        saved = json.loads(state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return initial
    return {**initial, **saved}


def save(state: dict) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


@contextmanager
def editing():
    """`with store.editing() as state:` 블록 안에서 바꾼 내용을 저장합니다."""
    with _LOCK:
        state = load()
        yield state
        save(state)


def reset() -> None:
    with _LOCK:
        state_path().unlink(missing_ok=True)
