"""욕설·비속어 가리기 (복복이 대화)

- 학생이 쓴 말: 욕설을 글자 수만큼 * 로 바꿔서 저장하고 보여 줍니다 (두 글자면 **).
- 복복이의 대답: 욕설이 든 문장은 내보내지 않습니다 (app/chatbot.py).
- 위험 신호를 살피는 일은 가리기 전의 말로 합니다. 가려서 신호를 놓치면 안 되기 때문입니다.

낱말 목록은 data/profanity.json 에 있습니다. 단순한 낱말 비교라서 놓치거나 잘못 가릴 수 있습니다.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator

from .data import DATA_DIR

_cfg = json.loads((DATA_DIR / "profanity.json").read_text(encoding="utf-8"))

# 글자 사이에 끼워 넣은 숫자·기호는 건너뛰고 찾음 (시1발, 씨.발). 띄어쓰기는 건너뛰지 않음 ('다시 발표')
_GAP = r"[^\s가-힣ㄱ-ㅎㅏ-ㅣA-Za-z]*"


def _pattern(word: str) -> str:
    if word.isascii():  # 영어는 낱말 단위로만
        return r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])"
    return _GAP.join(re.escape(ch) for ch in word)


def _any_of(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(patterns) or r"(?!)", re.IGNORECASE)


_WORDS = _any_of([_pattern(w) for w in sorted(_cfg["words"], key=len, reverse=True)])
_ALLOW = _any_of([r"\s*".join(re.escape(part) for part in w.split()) for w in sorted(_cfg["allow"], key=len, reverse=True)])


def _hits(text: str) -> Iterator[re.Match]:
    """욕설이 있는 자리. 욕이 아닌 표현(allow)과 겹치는 자리는 뺌"""
    safe = [m.span() for m in _ALLOW.finditer(text)]
    for m in _WORDS.finditer(text):
        if not any(start < m.end() and m.start() < end for start, end in safe):
            yield m


def has(text: str | None) -> bool:
    return bool(text) and next(_hits(text), None) is not None


def mask(text: str) -> str:
    """욕설을 글자 수만큼 * 로 바꿈"""
    out = list(text)
    for m in _hits(text):
        for i in range(m.start(), m.end()):
            if not out[i].isspace():
                out[i] = "*"
    return "".join(out)
