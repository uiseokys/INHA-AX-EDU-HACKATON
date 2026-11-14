"""보존 기록(var/ledger.jsonl)이 바뀌지 않았는지 확인

    python scripts/verify_ledger.py                 # 기본 위치(var/state.json 옆)의 보존 기록
    BOKBOK_STATE=/경로/state.json python scripts/verify_ledger.py

처음부터 끝까지 해시를 다시 계산합니다. 문제가 없으면 0, 바뀐 흔적이 있으면 1로 끝납니다.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import ledger, store  # noqa: E402


def main() -> None:
    state = store.load()
    result = ledger.verify(state.get("ledger_head"))
    print(f"보존 기록: {ledger.path()}")
    if result["ok"]:
        print(f"정상 · {result['count']}건 · 마지막 해시 {result['head']}")
        return
    print(f"위변조 의심 · {result['problem']} · {result['at']}번째 기록부터 확인 필요 (그 앞의 {result['count']}건은 정상)")
    sys.exit(1)


if __name__ == "__main__":
    main()
