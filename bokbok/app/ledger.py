"""기록의 무결성과 위변조 방지: 추가만 할 수 있는 보존 기록(ledger)

화면에 보이는 상태(var/state.json)는 고치거나 지울 수 있는 '작업용 사본'입니다.
이 모듈은 그와 별도로, 기록이 만들어지거나 바뀔 때마다 **원본을 한 줄씩 덧붙여** 남깁니다 (var/ledger.jsonl).

  1. 서버 기준 타임스탬프: 시각(ts)은 요청을 받은 서버의 시계로만 찍습니다. 브라우저가 보낸 시각은 쓰지 않습니다.
  2. 수정/삭제 불가 로그 구조: 이 모듈에는 '덧붙이기'와 '읽기'만 있습니다. 기록을 고치면 새 줄이 생기고,
     화면에서 지워도 '지웠다'는 줄이 생길 뿐 앞의 줄은 그대로 남습니다.
  3. 원본 보존 및 해시 기록: 각 줄은 원본(payload)과 그 해시(payload_hash)를 담고, 바로 앞줄의 해시(prev)를 함께 넣어
     해시를 계산합니다(hash). 그래서 중간의 한 글자만 바뀌어도, 한 줄이 빠지거나 순서가 바뀌어도 verify() 가 찾아냅니다.

한계: 서버 관리자가 파일 전체를 처음부터 다시 만들어 내는 것까지 막지는 못합니다. 그것까지 막으려면 가장 마지막 해시(head)를
주기적으로 외부(교육청 서버, 공증 서비스 등)에 맡겨 두어야 합니다. 화면의 '마지막 해시'가 그 용도입니다.
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime
from pathlib import Path

from . import store

GENESIS = "0" * 64  # 첫 줄의 '앞줄 해시'
_LOCK = threading.Lock()

# 기록 종류 → 화면에 보여 줄 이름
KINDS = {
    "record": "감정 기록",
    "share": "문장 공개 범위 변경",
    "chat": "복복이 대화",
    "chat_hide": "대화 기록 화면에서 지움",
    "alert": "위험 신호 알림",
    "alert_update": "알림 단계 변경",
    "alert_read": "선생님 알림 확인",
    "alert_task_planned": "알림 후속 조치 계획",
    "alert_task_completed": "알림 후속 조치 완료",
    "followup": "사후 관리 기록",
    "support_share": "교사 간 지원 메모 공유",
    "reset": "시연 데이터 초기화",
    "consent": "약속(동의)",
}


def path() -> Path:
    """상태 파일과 같은 폴더에 둡니다 (공개 체험 사이트에서는 방문자별 체험 공간마다 하나)."""
    return store.state_path().with_name("ledger.jsonl")


def server_now() -> str:
    """서버 시계 기준 현재 시각 (시간대 포함, 초 단위). 시연용 날짜 고정(BOKBOK_TODAY)과 무관하게 실제 시각을 씁니다."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _canonical(value) -> str:
    """같은 내용이면 항상 같은 글자가 되도록 정해진 방식으로 적기 (키 순서 고정, 공백 없음)"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def payload_hash(payload: dict) -> str:
    return _sha(_canonical(payload))


def entry_hash(e: dict) -> str:
    """한 줄의 해시: 순번·서버 시각·종류·대상·원본 해시·앞줄 해시를 함께 묶어 계산"""
    return _sha(_canonical([e["seq"], e["ts"], e["kind"], e["student_id"], e["ref"], e["payload_hash"], e["prev"]]))


def entries() -> list[dict]:
    """보존 기록 전체 (오래된 순). 읽을 수 없는 줄은 {"broken_line": 줄 번호} 로 표시"""
    try:
        lines = path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            out.append({"broken_line": i})
    return out


def append(kind: str, student_id: str | None, ref: str | None, payload: dict) -> dict:
    """원본을 한 줄 덧붙이고 그 줄을 돌려줌. 이 모듈에서 파일을 쓰는 유일한 곳이며, 덧붙이기 모드로만 엽니다."""
    assert kind in KINDS, kind
    with _LOCK:
        last = next((e for e in reversed(entries()) if "hash" in e), None)
        e = {
            "seq": (last["seq"] + 1) if last else 1,
            "ts": server_now(),
            "kind": kind,
            "student_id": student_id,
            "ref": ref,
            "payload": payload,
            "payload_hash": payload_hash(payload),
            "prev": last["hash"] if last else GENESIS,
        }
        e["hash"] = entry_hash(e)
        p = path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
        return e


def head() -> dict | None:
    """가장 마지막 줄의 순번과 해시. 이 값을 외부에 맡겨 두면 그 시점까지의 기록 전체를 증명할 수 있습니다."""
    last = next((e for e in reversed(entries()) if "hash" in e), None)
    return {"seq": last["seq"], "hash": last["hash"], "ts": last["ts"]} if last else None


def verify(expected_head: dict | None = None) -> dict:
    """처음부터 끝까지 다시 계산해 위변조 여부를 확인

    돌려주는 값: {"ok", "count", "head", "problem": 무엇이 잘못됐는지 | None, "at": 문제가 처음 드러난 순번 | None}
    expected_head: 따로 적어 둔 마지막 순번과 해시({"seq", "hash"}). 주면 '뒤쪽이 잘려 나갔는지'도 확인합니다.
    """
    prev, count = GENESIS, 0
    result = {"ok": True, "count": 0, "head": None, "problem": None, "at": None}

    def fail(problem: str, at: int) -> dict:
        return {**result, "ok": False, "count": count, "problem": problem, "at": at}

    for e in entries():
        at = count + 1
        if "broken_line" in e:
            return fail("읽을 수 없는 줄이 있어요 (형식이 깨짐)", at)
        if e.get("seq") != at:
            return fail("순번이 이어지지 않아요 (줄이 빠지거나 순서가 바뀜)", at)
        if e.get("prev") != prev:
            return fail("앞줄과의 연결이 끊겼어요 (앞쪽 기록이 바뀌거나 빠짐)", at)
        if payload_hash(e.get("payload", {})) != e.get("payload_hash"):
            return fail("원본 내용이 기록 당시와 달라요", at)
        if entry_hash(e) != e.get("hash"):
            return fail("시각·종류·대상 정보가 기록 당시와 달라요", at)
        prev, count = e["hash"], at
    result.update(count=count, head=prev if count else None)
    if expected_head and (expected_head.get("seq", 0) > count or
                          (expected_head.get("seq") == count and expected_head.get("hash") != prev)):
        return fail("따로 적어 둔 마지막 기록과 달라요 (뒤쪽 기록이 잘려 나감)", count + 1)
    return result
