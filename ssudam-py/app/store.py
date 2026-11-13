"""시연용 상태 저장소 (로컬 JSON 파일)

학생 화면과 교사 화면이 같은 파일을 읽기 때문에, 학생이 보낸 상담 요청이 교사 화면에 나타납니다.
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


def state_path() -> Path:
    default = Path(__file__).resolve().parent.parent / "var" / "state.json"
    return Path(os.environ.get("SSUDAM_STATE", default))


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def initial_state(today: str) -> dict:
    return {
        "version": 1,
        "todos": [
            {"id": "seed-1", "text": "수학 수행평가 자료 정리하기", "done": True, "date": today, "kind": "todo"},
            {"id": "seed-2", "text": "영어 단어 20개 외우기", "done": False, "date": today, "kind": "goal"},
            {"id": "seed-3", "text": "체육복 챙기기", "done": False, "date": today, "kind": "todo"},
        ],
        "my_logs": [],  # 시연용 학생(하늘)이 직접 남긴 감정 기록
        "skipped": [],  # 체크인을 건너뛴 날짜
        "share_overrides": {},  # 기록 id → 공유 여부
        # 시연을 위해 '어제 남긴 회고'를 미리 넣어 둡니다.
        "reflections": [
            {
                "date": add_days(today, -1),
                "moments": ["동아리", "수업"],
                "tomorrow_goal": "수학 오답노트 3문제 정리하기",
                "goal_result": None,
            }
        ],
        "consent": {"trend": False, "all_notes": False},
        "requests": [],
        "case_status": {},
        "events": {},
        "memos": {},
        "referrals": [],
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
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
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
