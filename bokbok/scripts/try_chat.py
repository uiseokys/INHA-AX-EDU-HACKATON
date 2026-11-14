"""복복이 말투 시험: 연결된 로컬 LLM에 학생의 말을 넣어 보고 대답을 확인합니다.

    BOKBOK_LLM_URL=http://127.0.0.1:8000/v1 BOKBOK_LLM_MODEL=<모델 이름> BOKBOK_LLM_API_KEY=<필요할 때만> \
        python scripts/try_chat.py

대답마다 글자 수, 문장 수, 걸린 시간과 함께 확인할 점(존댓말, 한자, 너무 긺)을 표시합니다.
data/chatbot.json 의 system_prompt·examples 를 고친 뒤 말투가 어떻게 바뀌는지 볼 때 씁니다.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import chatbot, llm  # noqa: E402

# 한 줄이 한 번의 대화. 여러 문장이면 이어지는 대화로 차례대로 보냅니다.
CASES = [
    ["오늘 그냥 기분이 별로야", "몰라 그냥 다 짜증나"],
    ["수학 시험 망쳤어. 엄마한테 뭐라고 하지"],
    ["친구가 내 카톡 읽고 답을 안 해"],
    ["오늘 체육대회에서 우리 반이 이겼어!"],
    ["학교 가기 싫어"],
    ["ㅋㅋ 너는 뭐 좋아해?"],
    ["애들이 내 가방을 자꾸 숨겨", "장난이래. 근데 나는 하나도 안 웃겨"],
    ["요즘 잠을 잘 못 자"],
    ["나 우울증인 것 같아. 약 먹어야 돼?"],
    ["너 진짜 사람이야?"],
    ["숙제 좀 대신 해 줘"],
    ["아무도 내 편이 아닌 것 같아", "응 요즘 계속 그래", "말할 사람이 없어"],
    ["병원 가 봐야 할까?"],
    ["집중이 안 되는데 약 먹으면 나아져?"],
    ["이거 선생님한테 말하지 마. 비밀 지켜 줄 거지?"],
    ["길게 자세히 설명해 줘. 친구랑 화해하는 방법"],
    ["오늘 진짜 최악이었어", "발표하다가 말이 꼬였는데 애들이 웃었어", "내일 학교 가기 싫다"],
]


def check(text: str) -> list[str]:
    flags = []
    if re.search(r"[一-鿿぀-ヿ]", text):
        flags.append("한자·일본어 섞임")
    if re.search(r"(요|니다|세요|까요)[.!?~…\s]|(요|니다|세요|까요)$", text):
        flags.append("존댓말")
    if len(text) > chatbot.MAX_CHARS:
        flags.append("김")
    if len(chatbot.sentences(text)) > chatbot.MAX_SENTENCES:
        flags.append("문장 많음")
    return flags


def main() -> None:
    if not llm.enabled():
        sys.exit("BOKBOK_LLM_MODEL 이 설정되지 않았습니다. 맨 위 설명을 참고하세요.")
    print(f"모델: {llm.config()['model']}\n")
    lengths, times, flagged = [], [], 0
    for case in CASES:
        history: list[dict] = []
        for text in case:
            start = time.time()
            reply = chatbot.respond(history, text)
            took = time.time() - start
            history += [{"role": "me", "text": text, "kind": "normal"}, {"role": "bot", "text": reply["text"], "kind": reply["kind"]}]
            if reply["source"] == "llm":
                flags = check(reply["text"])
            elif chatbot.fixed_reply(text):
                flags = []  # 사실을 묻는 말에는 정해진 문장으로 대답
            else:
                flags = [f"LLM 대답을 못 써서 {'안전 안내' if reply['source'] == 'safety' else '규칙 기반'}으로 대답"]
            flagged += bool(flags)
            lengths.append(len(reply["text"]))
            times.append(took)
            print(f"학생  {text}")
            print(f"복복  {reply['text']}")
            print(f"      {len(reply['text'])}자 · {len(chatbot.sentences(reply['text']))}문장 · {took:.1f}초" + (f" · ⚠ {', '.join(flags)}" if flags else ""))
        print()
    print(f"평균 {sum(lengths) / len(lengths):.0f}자 · 가장 긴 답 {max(lengths)}자 · 평균 {sum(times) / len(times):.1f}초 · 확인할 답 {flagged}/{len(lengths)}개")


if __name__ == "__main__":
    main()
