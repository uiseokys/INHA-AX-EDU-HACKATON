"""AI 마음 돌봄 챗봇 '복복이' (기획서 (3))

대답 순서
  1. 안전 확인: 학생의 말에서 자해·자살 같은 긴급 신호 키워드를 먼저 찾습니다. 찾으면 LLM에 맡기지 않고
     정해진 안전 안내 문구(data/chatbot.json 의 safety)와 109·1388·112 를 보여 줍니다.
     폭력·가정·온라인 피해가 의심되는 말에는 대화를 끊지 않고 평소처럼 대답합니다.
  2. 정해진 대답: "선생님한테 말할 거야?"처럼 사실을 묻는 말에는 정해진 문장으로 대답합니다.
  3. 로컬 LLM: BOKBOK_LLM_MODEL 이 설정돼 있으면 로컬 LLM으로 대답합니다 (app/llm.py).
  4. 규칙 기반: LLM이 없거나 실패하면 키워드에 맞는 미리 쓴 대답을 씁니다.

선생님께 전하기 (맨 아래 assess)
  도움이 필요해 보이면 대화 중에는 학생에게 알리지 않고 선생님께 전합니다 (가입할 때 동의했다고 가정).
  전해지는 것은 단계·분류·AI가 정리한 짧은 요약이고, 대화 원문은 전하지 않습니다.

말투와 길이 (로컬 LLM)
  - data/chatbot.json 의 system_prompt 와 examples(예시 대화)로 '친구처럼, 짧게' 말하도록 알려 줍니다.
  - 그래도 길게 말하면 tidy() 가 앞의 두 문장만 남깁니다.
  - 한자·일본어가 섞이거나, 존댓말을 쓰거나, 판정·진단처럼 들리는 말(avoid)을 하면 한 번 다시 묻고,
    그래도 남아 있으면 그 문장을 뺍니다. 이모지는 항상 뺍니다.
  - 대화가 누구에게 보이는지 같은 '사실'을 묻는 말(fixed)은 LLM에 맡기지 않고 정해진 문장으로 대답합니다.

욕설·비속어 (app/profanity.py, data/profanity.json)
  - 학생이 쓴 욕설은 글자 수만큼 * 로 바꿔 저장·표시합니다. 대답을 만들고 위험 신호를 살필 때는 원래 말을 봅니다.
  - 복복이의 대답에 욕설이 있으면 한 번 다시 묻고, 그래도 남아 있으면 그 문장을 뺍니다.
"""

from __future__ import annotations

import hashlib
import json
import re

from . import chat_emotions, llm, profanity
from .analysis import risk_hits
from .data import CHATBOT
from .models import EMOTIONS, INTENSITY_LABELS

HISTORY_FOR_LLM = 12  # LLM에 함께 보내는 최근 대화 수
MAX_SENTENCES = 2  # 복복이가 한 번에 말하는 문장 수
MAX_CHARS = 80  # 두 문장이 이보다 길면 첫 문장만 말함
REPLY_TOKENS = 120  # LLM이 한 번에 쓸 수 있는 길이
REPLY_TEMPERATURE = 0.4  # 낮을수록 차분하고 덜 지어냄 (높이면 표현이 다양해지지만 엉뚱한 말이 늘어남)

_FOREIGN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff]")  # 한자·일본어
_POLITE = re.compile(r"(?:요|니다|세요|까요|죠)(?=[.!?~…ㅠㅜㅋㅎ\s]|$)")  # 존댓말 끝맺음
_EMOJI = re.compile(r"\s*[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]+")
_QUOTED = re.compile(r"[\"“‘'][^\"“”‘’']*[\"”’']")  # 따라 말해 보라고 알려 주는 문장은 빼고 살핌


def sentences(text: str) -> list[str]:
    """문장 단위로 나누기. 문장 뒤에 붙은 이모지는 앞 문장에 둡니다."""
    out: list[str] = []
    for part in re.split(r"(?<=[.!?…~])\s+|\n+", text.strip()):
        m = re.match(r"^([^\w\s\"“‘'(]+)\s*(.*)$", part, re.S)
        if m and out:
            out[-1] += " " + m.group(1)
            part = m.group(2)
        if part.strip():
            out.append(part.strip())
    return out


def _unwanted(sentence: str) -> bool:
    """한자·일본어가 섞였거나, 복복이가 꺼내면 안 되는 말(판정·진단처럼 들리는 말, 욕설)이 있는지"""
    return bool(_FOREIGN.search(sentence)) or any(w in sentence for w in CHATBOT.get("avoid", [])) or profanity.has(sentence)


def off_tone(text: str) -> bool:
    """다시 물어볼 만한 대답인지: 한자·일본어, 판정·진단처럼 들리는 말, 욕설, 존댓말"""
    return _unwanted(text) or bool(_POLITE.search(_QUOTED.sub("", text)))


def fixed_reply(text: str) -> str | None:
    """대화가 누구에게 보이는지처럼 지어내면 안 되는 질문에는 정해진 문장으로 대답"""
    for item in CHATBOT.get("fixed", []):
        if any(k in text for k in item["keywords"]):
            return item["reply"]
    return None


def tidy(text: str) -> str:
    """LLM의 대답을 친구의 짧은 한마디로 다듬기: 한 줄, 최대 두 문장, 이모지 없이, 쓰면 안 되는 말이 든 문장 제외"""
    text = re.sub(r"^\s*복복이?\s*[:：]\s*", "", _EMOJI.sub("", text.replace("*", "")))
    text = re.sub(r"그런가\?", "그래?", text)  # 이 모델이 자주 쓰는 어색한 질문 끝맺음
    parts = [p for p in sentences(text) if not _unwanted(p)]
    casual = [p for p in parts if not _POLITE.search(_QUOTED.sub("", p))]
    parts = (casual or parts)[:MAX_SENTENCES]  # 존댓말 문장은 다른 문장이 남을 때만 뺌
    while len(parts) > 1 and len(" ".join(parts)) > MAX_CHARS:
        parts.pop()
    return " ".join(" ".join(p.split()) for p in parts)


def system_prompt() -> str:
    """지시문 + 말투 예시. 예시를 지난 대화처럼 넣으면 모델이 "또 그랬구나" 하고 착각하므로 지시문 안에 글로 넣습니다."""
    lines = [CHATBOT["system_prompt"]]
    examples = CHATBOT.get("examples", [])
    if examples:
        lines.append("\n말투 예시 (말투만 참고해. 이 친구와 실제로 나눈 대화가 아니야. 지금 친구는 처음 이야기하는 거야.)")
        lines += [f"친구: {ex['me']}\n복복이: {ex['bot']}" for ex in examples]
    return "\n".join(lines)


def llm_messages(history: list[dict], text: str) -> list[dict]:
    """지시문(말투 예시 포함) → 최근 대화 → 이번 말"""
    messages = [{"role": "system", "content": system_prompt()}]
    for m in history[-HISTORY_FOR_LLM:]:
        if m.get("kind") in ("normal", None):
            messages.append({"role": "assistant" if m["role"] == "bot" else "user", "content": m["text"]})
    messages.append({"role": "user", "content": text})
    return messages


def llm_reply(history: list[dict], text: str) -> str:
    messages = llm_messages(history, text)
    raw = llm.chat(messages, max_tokens=REPLY_TOKENS, temperature=REPLY_TEMPERATURE)
    if off_tone(raw):  # 한 번만 다시: 무엇이 틀렸는지 알려 주고 더 차분하게
        hinted = [{"role": "system", "content": messages[0]["content"] + "\n\n" + CHATBOT.get("retry_hint", "")}] + messages[1:]
        again = llm.chat(hinted, max_tokens=REPLY_TOKENS, temperature=REPLY_TEMPERATURE / 2)
        if not off_tone(again):
            raw = again
    reply = tidy(raw)
    if not reply:
        raise llm.LLMError("다듬고 나니 남은 대답이 없음")
    return reply


def _pick(options: list[str], seed: str) -> str:
    """같은 상황에서는 같은 대답이 나오도록 (시연·테스트 재현용)"""
    return options[int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(options)]


def greeting(seed: str) -> str:
    return _pick(CHATBOT["greeting"], seed)


def emotion_question(emotion: str, intensity: int | None) -> str:
    label = EMOTIONS[emotion].label
    if intensity in INTENSITY_LABELS:
        label = f"{label} · {INTENSITY_LABELS[intensity]}"
    return CHATBOT["emotion_question"].format(emotion=label)


def rule_reply(text: str, seed: str) -> str:
    for rule in CHATBOT["rules"]:
        if any(k in text for k in rule["keywords"]):
            return _pick(rule["replies"], seed + text)
    return _pick(CHATBOT["fallback"], seed + text)


def respond(history: list[dict], text: str) -> dict:
    """history: [{"role": "bot"|"me", "text": ...}] (이번 말 포함 전), text: 학생의 이번 말

    돌려주는 값: {"text", "kind": "normal"|"urgent", "source": "llm"|"rule"|"safety", "risk": [분류], "help": 도움 화면 분류|None}
    """
    hits = risk_hits(text)
    if any(h["id"] == "urgent" for h in hits):
        return {"text": CHATBOT["safety"]["urgent"], "kind": "urgent", "source": "safety", "risk": hits, "help": None}
    # 그 밖의 신호(폭력·가정·온라인)는 대화를 끊지 않고 평소처럼 대답하고, 도움 화면으로 가는 길만 조용히 붙임
    extra = {"risk": hits, "help": hits[0]["help"] if hits else None}

    fixed = fixed_reply(text)
    if fixed:
        return {"text": fixed, "kind": "normal", "source": "rule", **extra}

    seed = str(len(history))
    if llm.enabled():
        try:
            return {"text": llm_reply(history, text), "kind": "normal", "source": "llm", **extra}
        except llm.LLMError:
            pass  # 아래 규칙 기반 대답으로
    # LLM 없이 피해가 의심되는 말을 들었을 때는 엉뚱한 규칙 대답 대신 들어 주는 한마디
    return {"text": CHATBOT["safety"]["listen"] if hits else rule_reply(text, seed), "kind": "normal", "source": "rule", **extra}


def status() -> dict:
    cfg = llm.config()
    return {"enabled": cfg["model"] is not None, "model": cfg["model"], "url": cfg["url"]}


# ── 선생님께 조용히 전하기 ───────────────────────────────────────────────────
# 학생은 가입할 때 '도움이 필요해 보이면 선생님께 전해진다'는 약속에 동의했다고 보고,
# 대화 중에는 학생에게 따로 알리지 않습니다. 선생님께는 단계·분류·AI 요약만 전하고 대화 원문은 전하지 않습니다.

JUDGE_HISTORY = 8  # 판단할 때 함께 보는 학생의 최근 말 수
CARE_MIN_MESSAGES = 3  # '마음이 힘들어 보임'은 한두 마디로는 전하지 않음
LEVEL_ORDER = {"none": 0, "care": 1, "issue": 2, "urgent": 3}
TOPIC_CATEGORY = {"school": "violence", "home": "home", "online": "online", "mind": "mind"}


def judge(texts: list[str]) -> dict | None:
    """학생이 한 말(오래된 순)을 로컬 LLM에게 보여 주고 {"level", "topic", "summary"} 를 받음. 못 받으면 None"""
    if not texts or not llm.enabled() or "judge" not in CHATBOT:
        return None
    said = " ".join(f"{i}. {t}" for i, t in enumerate(texts, 1))
    messages = [{"role": "system", "content": CHATBOT["judge"]["prompt"]}, {"role": "user", "content": f"학생의 말: {said}"}]
    try:
        raw = llm.chat(messages, max_tokens=200, temperature=0.1)
    except llm.LLMError:
        return None
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        out = json.loads(m.group(0)) if m else None
    except ValueError:
        return None
    if not isinstance(out, dict) or out.get("level") not in LEVEL_ORDER:
        return None
    topic = out.get("topic") if out.get("topic") in TOPIC_CATEGORY else "mind"
    summary = " ".join(str(out.get("summary") or "").split())[:160]
    if any(len(t) >= 8 and t in summary for t in texts):  # 학생의 말을 그대로 옮긴 요약은 쓰지 않음
        summary = ""
    return {"level": out["level"], "topic": topic, "summary": summary}


def assess(said_before: list[str], text: str, reply: dict) -> list[dict]:
    """이번 말까지 보고 선생님께 전할 신호를 정함. [{"category", "level", "note"}] (전할 것이 없으면 빈 목록)

    said_before: 오늘 학생이 앞서 한 말, text: 이번 말, reply: respond() 의 결과
    키워드로 찾은 신호는 LLM이 없어도 전하고, LLM이 있으면 대화 흐름을 보고 단계와 요약을 더합니다.
    """
    signals = {h["id"]: {"category": h["id"], "level": "urgent" if h["id"] == "urgent" else "issue", "note": None}
               for h in reply.get("risk", [])}
    texts = (said_before + [text])[-JUDGE_HISTORY:]
    found = judge(texts)
    if found and found["level"] != "none" and not (found["level"] == "care" and len(texts) < CARE_MIN_MESSAGES):
        category = "urgent" if found["level"] == "urgent" else TOPIC_CATEGORY[found["topic"]]
        if found["level"] != "urgent" and category == "mind" and found["level"] == "issue":
            found["level"] = "care"  # 구체적인 피해 없이 마음 상태만 이야기한 경우
        sig = signals.setdefault(category, {"category": category, "level": found["level"], "note": None})
        if LEVEL_ORDER[found["level"]] > LEVEL_ORDER[sig["level"]]:
            sig["level"] = found["level"]
        sig["note"] = found["summary"] or None
    return list(signals.values())


def converse(history: list[dict], text: str, today: str) -> tuple[dict, list[dict]]:
    """한 번의 대화: 복복이의 대답과, 선생님께 조용히 전할 신호를 함께 돌려줌

    키워드에는 없지만 대화 흐름상 긴급하다고 판단되면, 그날 처음 한 번은 대답을 안전 안내로 바꿉니다
    (학생에게 109·1388·112 를 보여 주기 위해서이고, 선생님께 전했다는 말은 하지 않습니다).
    """
    reply = respond(history, text)
    said_before = [m["text"] for m in history if m["role"] == "me" and m.get("date") == today and m.get("kind") in ("normal", None)]
    signals = assess(said_before, text, reply)
    shown_today = any(m["role"] == "bot" and m.get("date") == today and m.get("kind") == "urgent" for m in history)
    if reply["kind"] != "urgent" and not shown_today and any(s["level"] == "urgent" for s in signals):
        reply = {**reply, "text": CHATBOT["safety"]["urgent"], "kind": "urgent", "source": "safety", "help": None}
    if reply["source"] == "llm" and not any(s["level"] == "urgent" for s in signals):
        reply["emotions"] = chat_emotions.classify(said_before, text)
    if profanity.has(reply["text"]):  # 어느 길로 만든 대답이든 욕설은 화면에 내보내지 않음
        reply = {**reply, "text": profanity.mask(reply["text"])}
    return reply, signals


# ── 날짜별 대화 기록 (학생 본인만 봄) ────────────────────────────────────────

SUMMARY_MAX_MESSAGES = 20  # 하루 요약을 만들 때 보는 학생의 말 수
_VERDICT_WORDS = ("학교폭력", "왕따", "가해자", "우울증")


def day_summary(said: list[str]) -> tuple[str, str]:
    """학생이 하루 동안 한 말을 한두 문장으로 요약. (요약, "llm" | "rule")

    로컬 LLM이 없거나, 요약이 비었거나 판정처럼 들리는 말을 쓰면 '몇 번 이야기했는지'만 적습니다.
    """
    fallback = CHATBOT["daily"]["fallback"].format(n=len(said))
    if not said or not llm.enabled():
        return fallback, "rule"
    numbered = " ".join(f"{i}. {t}" for i, t in enumerate(said[-SUMMARY_MAX_MESSAGES:], 1))
    messages = [{"role": "system", "content": CHATBOT["daily"]["prompt"]}, {"role": "user", "content": f"학생의 말: {numbered}"}]
    try:
        raw = llm.chat(messages, max_tokens=120, temperature=0.2)
    except llm.LLMError:
        return fallback, "rule"
    text = " ".join(re.sub(r'["“”*]', "", _EMOJI.sub("", raw)).split())
    text = " ".join(sentences(text)[:2])[:140]
    if not text or _FOREIGN.search(text) or any(w in text for w in _VERDICT_WORDS):
        return fallback, "rule"
    return text, "llm"
