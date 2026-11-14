"""시연용 상태 저장소 (로컬 JSON 파일)

학생 화면과 교사 화면이 같은 파일을 읽기 때문에, 학생이 남긴 기록·신청이 교사 화면에 나타납니다.

· 기본(내 컴퓨터에서 실행): 상태 파일 하나를 모든 접속자가 함께 씁니다.
· 공개 테스트 모드(BOKBOK_MULTI=1): 브라우저마다 따로 체험 공간을 만들어, 다른 사람이 한 일이 섞이지 않습니다.
  쿠키에 담긴 무작위 체험 번호로 구분하며, 오래된 체험 공간은 자동으로 지웁니다.

⚠️ 시연용 구현입니다. 로그인·암호화·접근 제어 등 민감정보 보호 기능은 구현되어 있지 않습니다.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from .dates import add_days, today_key

_LOCK = threading.Lock()
BASE = Path(__file__).resolve().parent.parent


# ── 공개 테스트 모드: 브라우저별 체험 공간 ─────────────────────────────────────

SESSION_COOKIE = "bokbok_sandbox"
SESSION_MAX_AGE = 3 * 24 * 3600  # 체험 공간 보관 기간(초)
SESSION_MAX_COUNT = 300  # 동시에 보관할 최대 체험 공간 수
_SID = re.compile(r"^[0-9a-f]{32}$")
_session: ContextVar[str | None] = ContextVar("bokbok_session", default=None)


def multi_mode() -> bool:
    return os.environ.get("BOKBOK_MULTI", "") not in ("", "0", "false")


def sessions_dir() -> Path:
    return Path(os.environ.get("BOKBOK_SESSIONS", BASE / "var" / "sessions"))


def valid_sid(sid: str | None) -> bool:
    return bool(sid and _SID.match(sid))


def new_sid() -> str:
    prune_sessions()
    return uuid.uuid4().hex


def use_session(sid: str | None):
    """이번 요청이 쓸 체험 공간을 정함 (미들웨어에서 호출). 돌려준 토큰으로 되돌릴 수 있음"""
    return _session.set(sid if valid_sid(sid) else None)


def prune_sessions() -> None:
    """오래됐거나 너무 많이 쌓인 체험 공간 지우기"""
    root = sessions_dir()
    if not root.is_dir():
        return
    dirs = sorted((d for d in root.iterdir() if d.is_dir() and valid_sid(d.name)), key=lambda d: d.stat().st_mtime)
    now = time.time()
    for i, d in enumerate(dirs):
        if now - d.stat().st_mtime > SESSION_MAX_AGE or len(dirs) - i > SESSION_MAX_COUNT:
            shutil.rmtree(d, ignore_errors=True)


def _session_root() -> Path | None:
    sid = _session.get()
    return sessions_dir() / sid if sid else None


def state_path() -> Path:
    root = _session_root()
    if root:
        return root / "state.json"
    return Path(os.environ.get("BOKBOK_STATE", BASE / "var" / "state.json"))


def upload_dir() -> Path:
    root = _session_root()
    path = root / "uploads" if root else Path(os.environ.get("BOKBOK_UPLOADS", BASE / "var" / "uploads"))
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
        "record_later": None,  # 오늘 감정 기록을 '나중에 할게요'로 미룬 날짜. 그날은 홈을 바로 보여 줌
        "share_overrides": {},  # 기록 id → 선생님께 문장 보여 주기 여부
        # 시연용 학생과 복복이의 대화 (날짜별로 묶어 보여 줌). 처음에는 지난 이틀 치 예시 대화가 들어 있음
        "chats": [
            {"id": f"M-seed-{i}", "role": m["role"], "date": day(m["day_offset"]), "time": m["time"], "text": m["text"],
             "kind": "normal", "source": "rule"}
            for i, m in enumerate(seed.get("chats", []))
        ],
        # 날짜 → {"summary": 하루 요약, "count": 요약할 때 학생이 한 말 수, "source": llm | rule}
        "chat_days": {day(int(off)): dict(v) for off, v in seed.get("chat_days", {}).items()},
        "alerts": [
            {**{k: v for k, v in a.items() if k != "day_offset"}, "date": day(a["day_offset"]), "time": "16:40", "read": False}
            for a in seed["alerts"]
        ],
        "followups": dict(seed["followups"]),
        "followup_notes": {},
        "support_shares": [],
        "conversation_requests": [],
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
