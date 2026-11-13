# 복복복 · 학생 마음 돌봄 플랫폼

2026 INHA AX-EDU 해커톤 시연용 웹 프로토타입 (Python · FastAPI · Jinja2)

> **시연용 프로토타입입니다.** 학교·선생님·학생 정보는 모두 합성 데이터이며 실제 정보가 아닙니다.
> 분석 결과는 진단이 아닌 참고 정보이고, 로그인·암호화·접근 제어 같은 민감정보 보호 기능은 구현되어 있지 않습니다.
> 상태는 서버의 로컬 파일(`var/state.json`) 하나에 저장되며, 접속한 모든 사람이 함께 씁니다.

## 실행

Python 3.10 이상이 필요합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload     # http://localhost:8000
```

```bash
pytest                            # 분석·포인트·챗봇 로직 + 화면 흐름 테스트
python scripts/generate_data.py   # 합성 감정 기록 다시 만들기
./scripts/build_css.sh            # 화면의 Tailwind 클래스를 바꿨을 때만 (Node.js 필요)
```

- 날짜를 고정해 시연하려면 `BOKBOK_TODAY=2026-11-14 uvicorn app.main:app` 처럼 실행합니다.
- 화면 아래 **시연 데이터 초기화** 버튼(또는 `var/state.json` 삭제)으로 처음 상태로 돌아갑니다.

## 공개 테스트 사이트 (Render)

다른 팀이 체험할 수 있도록 [Render](https://render.com) 무료 요금제에 올릴 수 있게 설정해 두었습니다 (저장소 맨 위 `render.yaml`).

1. Render에 GitHub 계정으로 로그인 → **New → Blueprint** → 이 저장소 선택 → **Deploy Blueprint**
2. 몇 분 뒤 `https://<서비스 이름>.onrender.com` 주소가 생깁니다.

- `BOKBOK_MULTI=1`: **방문자(브라우저)마다 따로 체험 공간**이 만들어져서, 다른 팀이 한 일과 섞이지 않습니다. 체험 공간은 3일 뒤, 또는 서버가 다시 시작되면 지워집니다.
- `TZ=Asia/Seoul`: 오늘 날짜와 시간을 한국 기준으로 계산합니다.
- 무료 요금제는 한동안 접속이 없으면 잠들었다가, 다음 접속 때 1분 정도 걸려 깨어납니다.
- 공개 서버에는 로컬 LLM이 없으므로 복복이는 규칙 기반으로 대답합니다.
- 다른 서비스에 올릴 때는 `Dockerfile`을 쓰면 됩니다.

## 챗봇 '복복이'와 로컬 LLM

복복이는 **OpenAI 호환 Chat Completions API**를 제공하는 로컬 서버(Ollama, LM Studio, llama.cpp server, vLLM 등)에 연결할 수 있습니다.
모델은 정해 두지 않았고, 환경변수로 지정합니다.

| 환경변수 | 뜻 | 기본값 |
| --- | --- | --- |
| `BOKBOK_LLM_MODEL` | 사용할 모델 이름. **비어 있으면 LLM 없이 규칙 기반으로 대답** | 없음 |
| `BOKBOK_LLM_URL` | 서버 주소 | `http://localhost:11434/v1` (Ollama) |
| `BOKBOK_LLM_API_KEY` | 서버가 요구할 때만 | 없음 |
| `BOKBOK_LLM_TIMEOUT` | 응답 대기 시간(초) | `40` |

```bash
BOKBOK_LLM_MODEL=<받아 둔 모델 이름> uvicorn app.main:app --reload
```

대답 순서 (`app/chatbot.py`)
1. **안전 확인이 먼저**: 학생의 말에서 위험 신호 키워드(`data/signals.json`)를 찾으면 LLM에 맡기지 않고, 정해 둔 안전 안내(109·1388·112, 선생님 상담, 전문기관, “지금 안전한 곳에 있나요?”)로 대답하고 담임 선생님께 알림을 남깁니다.
2. **로컬 LLM**: 모델이 설정돼 있으면 `data/chatbot.json`의 `system_prompt`와 최근 대화를 함께 보내 대답합니다.
3. **규칙 기반**: 모델이 없거나 연결에 실패하면 키워드에 맞춰 미리 쓴 대답을 씁니다. 그래서 LLM이 꺼져 있어도 시연은 끊기지 않습니다.

대화 내용은 선생님께 공개되지 않습니다. 알림에는 ‘도움이 필요할 수 있다’는 사실과 분류만 담깁니다.
채팅 화면 머리말의 표시(‘로컬 AI 연결됨’ / ‘규칙 기반 응답’)로 현재 상태를 확인할 수 있습니다.

## 시연 흐름

1. `/` → **학생으로 시작하기** → 처음 접속하면 학기 초 **기본 정보** 입력 (건너뛰기 가능)
2. `/student` 홈에서 **감정 스티커** 선택 → 감정 단어 → 짧은 문장 → 기록하고 포인트 받기
3. 부정 감정을 기록하면 포인트 적립 화면에 **복복이 대화 권유**가 함께 뜸 (‘지금은 괜찮아요’로 거절 가능)
4. `/student/chat` 에서 복복이와 대화. 위험한 표현을 말하면 안전 안내가 뜨고 선생님께 알림
5. `/teacher` 상단에 **카톡 공지처럼 고정된 알림**, 학생별 확인 목록에서 ‘상담 권장’ 확인 → 학생 상세 리포트
6. `/student/counsel` 에서 선생님이 열어 둔 시간으로 **상담 신청** → `/teacher/counsel` 에서 확정
7. `/student/shop` 에서 포인트로 **상품 교환 신청** → `/teacher/shop` 에서 승인

## 기획서 기능과 화면

| 기획서 | 학생 화면 | 선생님 화면 |
| --- | --- | --- |
| (1) 학생 기본 정보 | `/student/welcome` | 학생 상세 › 기본 정보 |
| (2)-1 감정 기록 | `/student/record` | 학생 상세 › 최근 감정 기록 |
| (2)-2 AI 감정 분석 리포트 | `/student/report` | `/teacher`, 학생 상세 › 감정 리포트·권장 조치 |
| (3) 복복이 챗봇 | `/student/chat` | `/teacher/alerts`, 상단 고정 알림 |
| (4) 외부 상담·지원기관 연계 | `/student/help`, `/student/counsel` | `/teacher/counsel` |
| (5) 포인트·우리 반 상점 | `/student/points`, `/student/shop` | `/teacher/shop` |
| ⑥ 지속적인 사후 관리 | — | 학생 상세 › 사후 관리 |

## 폴더 구조

```
app/
  main.py         FastAPI 라우트 (화면 GET, 버튼 동작 POST → 리다이렉트, 챗봇 /api/chat)
  analysis.py     규칙 기반 감정 분석 (학생 리포트, 교사 리포트, 위험 신호)
  chatbot.py      복복이 대답 순서 (안전 확인 → 로컬 LLM → 규칙 기반)
  llm.py          로컬 LLM 연결 (OpenAI 호환 API)
  points.py       포인트 계산 (기록 참여에 대해서만 지급)
  data.py         합성 데이터 + 저장된 상태 조회
  store.py        로컬 JSON 파일 상태 저장소
  charts.py       그래프 좌표 계산
  models.py       서비스 이름, 감정(기획서 색상), 학생 상태 단계
  templates/      Jinja2 화면 (_ui.html: 복복이 캐릭터·감정 스티커·그래프 등 공통 조각)
  static/         app.css(빌드 결과) · app.js(보조 스크립트) · src/input.css(스타일 원본)
data/             합성 데이터와 문구 (data/README.md 참고)
scripts/          generate_data.py · build_css.sh
tests/            test_logic.py · test_app.py
```

## 팀에서 채워 주실 부분

- `data/help.json`: ‘도움이 필요할 때’ 각 항목의 상황 설명·사례·대처 방법·지원기관. 지금은 임시 문구이며 화면에도 ‘임시 문구’로 표시됩니다.
- `data/chatbot.json`: 복복이의 말투, 규칙 기반 대답, 안전 안내 문구.
- 서비스 이름은 `app/models.py`의 `SERVICE_NAME` 하나만 바꾸면 됩니다.
