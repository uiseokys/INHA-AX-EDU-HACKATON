"""로컬 LLM 연결

Ollama, LM Studio, llama.cpp server, vLLM 등 'OpenAI 호환 Chat Completions API'를 제공하는
로컬 서버라면 어떤 것이든 연결할 수 있습니다. 모델은 정해 두지 않았고, 환경변수로 지정합니다.

  BOKBOK_LLM_MODEL    사용할 모델 이름 (비어 있으면 LLM을 쓰지 않고 규칙 기반으로 대답)
  BOKBOK_LLM_URL      서버 주소 (기본값: Ollama의 http://localhost:11434/v1)
  BOKBOK_LLM_API_KEY  서버가 요구할 때만 (대부분의 로컬 서버는 필요 없음)
  BOKBOK_LLM_TIMEOUT  응답 대기 시간(초, 기본 40)

예) Ollama:    BOKBOK_LLM_MODEL=<받아 둔 모델 이름> uvicorn app.main:app
    LM Studio: BOKBOK_LLM_URL=http://localhost:1234/v1 BOKBOK_LLM_MODEL=<모델 이름> uvicorn app.main:app
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request

log = logging.getLogger("bokbok.llm")


def config() -> dict:
    return {
        "model": os.environ.get("BOKBOK_LLM_MODEL", "").strip() or None,
        "url": os.environ.get("BOKBOK_LLM_URL", "http://localhost:11434/v1").rstrip("/"),
        "api_key": os.environ.get("BOKBOK_LLM_API_KEY", "").strip() or None,
        "timeout": float(os.environ.get("BOKBOK_LLM_TIMEOUT", "40")),
    }


def enabled() -> bool:
    return config()["model"] is not None


class LLMError(RuntimeError):
    pass


def chat(messages: list[dict], max_tokens: int = 300, temperature: float = 0.7) -> str:
    """messages: [{"role": "system"|"user"|"assistant", "content": str}] → 모델의 대답"""
    cfg = config()
    if not cfg["model"]:
        raise LLMError("BOKBOK_LLM_MODEL 이 설정되지 않았습니다.")
    body = json.dumps(
        {"model": cfg["model"], "messages": messages, "max_tokens": max_tokens, "temperature": temperature, "stream": False}
    ).encode()
    headers = {"Content-Type": "application/json"}
    if cfg["api_key"]:
        headers["Authorization"] = f"Bearer {cfg['api_key']}"
    req = urllib.request.Request(f"{cfg['url']}/chat/completions", data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as res:
            data = json.loads(res.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"] or ""
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as e:
        log.warning("로컬 LLM 호출 실패: %s", e)
        raise LLMError(str(e)) from e
    # 생각 과정을 함께 내보내는 모델의 <think> 부분은 학생에게 보여 주지 않음
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    if not text:
        raise LLMError("빈 응답")
    return text[:600]
