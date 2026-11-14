#!/bin/sh
# 내 컴퓨터의 로컬 LLM(oMLX)을 공개 테스트 사이트(Render)에서 쓰게 하기
#
#   ./scripts/share_local_llm.sh        # 실행해 두는 동안만 연결됩니다. 멈추려면 Ctrl+C
#
# 하는 일: Cloudflare 임시 터널로 이 컴퓨터의 oMLX(127.0.0.1:8000)에 닿는 https 주소를 하나 만듭니다.
#   - 주소는 실행할 때마다 바뀝니다. 바뀐 주소를 Render 환경변수 BOKBOK_LLM_URL 에 다시 넣어야 합니다.
#   - 주소를 아는 사람은 누구나 이 컴퓨터의 oMLX 에 요청을 보낼 수 있습니다. oMLX 의 API 키가 유일한 잠금이므로
#     키를 저장소·채팅·화면 공유에 남기지 마세요. 시연이 끝나면 이 스크립트를 끄세요.
#   - 공개 사이트 방문자가 복복이에게 한 말이 이 컴퓨터로 전해져 처리됩니다.
#   - 이 컴퓨터가 잠들거나 이 스크립트가 꺼지면, 공개 사이트의 복복이는 규칙 기반 대답으로 돌아갑니다.
#
# 필요한 것: cloudflared (brew install cloudflared), 실행 중인 oMLX
set -e

LLM_PORT="${LLM_PORT:-8000}"
MODEL="${BOKBOK_LLM_MODEL:-Qwen3-Next-80B-A3B-Instruct-oQ4}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared 가 설치되어 있지 않습니다. 먼저 설치하세요:  brew install cloudflared" >&2
  exit 1
fi
if ! curl -s -o /dev/null -m 3 "http://127.0.0.1:${LLM_PORT}/v1/models"; then
  echo "이 컴퓨터의 ${LLM_PORT}번 포트에서 로컬 LLM(oMLX)이 응답하지 않습니다. oMLX 를 먼저 켜 주세요." >&2
  exit 1
fi

cat <<GUIDE

로컬 LLM을 인터넷에 여는 중입니다. 잠시 뒤 아래쪽에 다음과 같은 주소가 나옵니다.

    https://<임의의-이름>.trycloudflare.com

Render 대시보드 → bokbok 서비스 → Environment 에 다음 세 값을 넣고 저장하세요 (저장하면 다시 배포됩니다).

    BOKBOK_LLM_URL      위 주소 뒤에 /v1 을 붙인 값   예) https://<임의의-이름>.trycloudflare.com/v1
    BOKBOK_LLM_MODEL    ${MODEL}
    BOKBOK_LLM_API_KEY  oMLX 의 API 키 (oMLX 설정 화면 또는 ~/.omlx/settings.json 의 auth.api_key)

이 창을 닫거나 Ctrl+C 를 누르면 연결이 끊깁니다. 켜 두는 동안 컴퓨터가 잠들지 않게 해 둡니다.

GUIDE

# caffeinate: 터널이 떠 있는 동안 컴퓨터가 잠들지 않게 함 (macOS 기본 도구)
if command -v caffeinate >/dev/null 2>&1; then
  exec caffeinate -i cloudflared tunnel --url "http://127.0.0.1:${LLM_PORT}"
fi
exec cloudflared tunnel --url "http://127.0.0.1:${LLM_PORT}"
