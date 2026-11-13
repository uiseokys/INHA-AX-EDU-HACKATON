"""AI 마음 돌봄 챗봇 '복복이' (기획서 (3))

대답 순서
  1. 안전 확인: 학생의 말에서 위험 신호 키워드를 먼저 찾습니다. 찾으면 LLM에 맡기지 않고
     정해진 안전 안내 문구(data/chatbot.json 의 safety)로 대답하고, 교사 알림을 남깁니다.
  2. 로컬 LLM: BOKBOK_LLM_MODEL 이 설정돼 있으면 로컬 LLM으로 대답합니다 (app/llm.py).
  3. 규칙 기반: LLM이 없거나 실패하면 키워드에 맞는 미리 쓴 대답을 씁니다.

대화 내용은 교사에게 공개하지 않습니다. 교사 알림에는 '도움이 필요할 수 있다'는 사실과 분류만 담깁니다.
"""

from __future__ import annotations

import hashlib

from . import llm
from .analysis import risk_hits
from .data import CHATBOT

HISTORY_FOR_LLM = 12  # LLM에 함께 보내는 최근 대화 수


def _pick(options: list[str], seed: str) -> str:
    """같은 상황에서는 같은 대답이 나오도록 (시연·테스트 재현용)"""
    return options[int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(options)]


def greeting(after_negative: bool, seed: str) -> str:
    return CHATBOT["greeting_after_negative"] if after_negative else _pick(CHATBOT["greeting"], seed)


def rule_reply(text: str, seed: str) -> str:
    for rule in CHATBOT["rules"]:
        if any(k in text for k in rule["keywords"]):
            return _pick(rule["replies"], seed + text)
    return _pick(CHATBOT["fallback"], seed + text)


def respond(history: list[dict], text: str) -> dict:
    """history: [{"role": "bot"|"me", "text": ...}] (이번 말 포함 전), text: 학생의 이번 말

    돌려주는 값: {"text", "kind": "normal"|"safety"|"urgent", "source": "llm"|"rule"|"safety", "risk": [분류]}
    """
    hits = risk_hits(text)
    if hits:
        urgent = any(h["id"] == "urgent" for h in hits)
        return {
            "text": CHATBOT["safety"]["urgent"] if urgent else CHATBOT["safety"]["check"],
            "kind": "urgent" if urgent else "safety",
            "source": "safety",
            "risk": hits,
        }

    seed = str(len(history))
    if llm.enabled():
        messages = [{"role": "system", "content": CHATBOT["system_prompt"]}]
        for m in history[-HISTORY_FOR_LLM:]:
            if m.get("kind") in ("normal", None):
                messages.append({"role": "assistant" if m["role"] == "bot" else "user", "content": m["text"]})
        messages.append({"role": "user", "content": text})
        try:
            return {"text": llm.chat(messages), "kind": "normal", "source": "llm", "risk": []}
        except llm.LLMError:
            pass  # 아래 규칙 기반 대답으로
    return {"text": rule_reply(text, seed), "kind": "normal", "source": "rule", "risk": []}


def status() -> dict:
    cfg = llm.config()
    return {"enabled": cfg["model"] is not None, "model": cfg["model"], "url": cfg["url"]}
