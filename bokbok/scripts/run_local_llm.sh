#!/bin/sh
# 로컬 LLM(oMLX)과 함께 복복복 실행하기
#
#   ./scripts/run_local_llm.sh              # 복복복 서버 실행 → http://localhost:8020
#   ./scripts/run_local_llm.sh try          # 서버 대신 말투 시험(scripts/try_chat.py) 실행
#   ./scripts/run_local_llm.sh judge        # 선생님께 전할 단계 판단 시험(scripts/try_judge.py) 실행
#
# - oMLX가 8000번 포트를 쓰므로 복복복은 8020번으로 띄웁니다 (PORT=... 로 바꿀 수 있음).
# - 모델을 바꾸려면 BOKBOK_LLM_MODEL=<모델 이름> ./scripts/run_local_llm.sh
# - API 키는 BOKBOK_LLM_API_KEY 가 있으면 그것을, 없으면 이 컴퓨터의 oMLX 설정(~/.omlx/settings.json)에서
#   읽어 씁니다. 키는 이 컴퓨터 안의 oMLX에만 보내며, 파일이나 화면에 남기지 않습니다.
set -e
cd "$(dirname "$0")/.."

export BOKBOK_LLM_URL="${BOKBOK_LLM_URL:-http://127.0.0.1:8000/v1}"
export BOKBOK_LLM_MODEL="${BOKBOK_LLM_MODEL:-Qwen3-Next-80B-A3B-Instruct-oQ4}"
if [ -z "$BOKBOK_LLM_API_KEY" ] && [ -f "$HOME/.omlx/settings.json" ]; then
  BOKBOK_LLM_API_KEY="$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.omlx/settings.json'))).get('auth',{}).get('api_key') or '')")"
  export BOKBOK_LLM_API_KEY
fi

PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
if [ "$1" = "try" ]; then
  exec "$PY" scripts/try_chat.py
fi
if [ "$1" = "judge" ]; then
  exec "$PY" scripts/try_judge.py
fi
exec "$PY" -m uvicorn app.main:app --port "${PORT:-8020}"
