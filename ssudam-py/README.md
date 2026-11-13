# 쓰담 (SSUDAM) — Python 버전

AI 감정 변화 분석 기반 학교폭력 피해학생 조기 발견 및 지원전문기관 연계 서비스 — 2026 INHA AX-EDU 해커톤 시연용 웹 프로토타입 (FastAPI + Jinja2)

> **시연용 프로토타입입니다.** 학생·학교·기관 정보는 모두 합성 데이터이며, 분석 결과는 진단이나 판정이 아닌 참고 정보입니다.
> 기록은 서버의 로컬 파일(`var/state.json`) 하나에 저장되고 접속한 모든 사람이 함께 씁니다.
> 로그인·암호화·접근 제어 같은 민감정보 보호 기능은 구현되어 있지 않습니다.

## 실행

Python 3.10 이상이 필요합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload     # http://localhost:8000
```

```bash
pytest                            # 분석 로직 + 화면 흐름 테스트
python scripts/generate_data.py   # 합성 감정 기록 재생성
./scripts/build_css.sh            # 화면의 Tailwind 클래스를 바꿨을 때만 (Node.js 필요)
```

- 오늘 날짜를 고정해 시연하려면 `SSUDAM_TODAY=2026-11-13 uvicorn app.main:app` 처럼 실행합니다.
- 화면 아래 **시연 데이터 초기화** 버튼(또는 `var/state.json` 삭제)으로 처음 상태로 되돌릴 수 있습니다.

## 시연 흐름

1. `/` 에서 **학생으로 시작하기**
2. `/student` 에서 오늘의 할 일 확인 → 감정 이모지 선택 → **기록하기**
3. 같은 화면의 그래프 맨 오른쪽에 오늘 기록이 반영된 것 확인 (`/student/insights` 에서 분석 근거 확인)
4. `/student/support` 에서 **상담 지원 요청 보내기** (공유 범위 선택 가능)
5. `/teacher` 에서 방금 보낸 요청(하늘 · 새 요청) 확인 → 학생 상세
6. **지원기관 찾아보기** → `/teacher/agencies` 에서 유형·지역 선택 → **연결 요청**

## 폴더 구조

```
app/
  main.py             FastAPI 라우트 (화면 조회 GET, 버튼 동작 POST → 리다이렉트)
  analysis.py         규칙 기반 Mock AI (이동평균 · 기간 비교 · 주제 분류 · 변화 시점)
  privacy.py          교사 화면에 전달할 기록을 공유 동의 범위로 거르는 함수
  data.py             합성 데이터 + 저장된 상태 조회 함수
  store.py            로컬 JSON 파일 상태 저장소
  charts.py           그래프 좌표 계산 (차트 라이브러리 없이 SVG + HTML로 서버에서 그림)
  models.py           자료형(EmotionLog, Consent)과 감정·진행 상태 상수
  dates.py            날짜 도우미
  icons.json          화면에 쓰는 Lucide 아이콘(ISC 라이선스) SVG 데이터
  templates/          Jinja2 화면 템플릿 (_ui.html: 공통 조각)
  static/             app.css(빌드 결과) · app.js(보조 스크립트) · src/input.css(스타일 원본)
data/                 합성 데이터 (data/README.md 참고)
scripts/              generate_data.py · build_css.sh
tests/                test_analysis.py · test_app.py
```

## 화면이 동작하는 방식

- 모든 화면은 서버(Python)가 그려서 보냅니다. 버튼은 폼 전송이고, 처리 후 원래 화면으로 돌아옵니다.
- 감정 선택 시 강도 입력이 나타나는 등의 반응은 CSS만으로 처리했습니다. `app.js`는 스크롤 위치 유지, 스위치 즉시 저장 같은 보조 기능만 담당하며 꺼져 있어도 기능은 동작합니다.
- `/docs` 에서 FastAPI가 자동으로 만든 라우트 목록을 볼 수 있습니다.

## 실제 AI 모델을 붙이려면

- **`app/analysis.py`의 `analyze()`** 가 유일한 분석 진입점입니다. 입력 `list[EmotionLog]`, 출력 `Insight` 형태만 유지하면 화면 코드는 그대로 동작합니다.
  - 주제 분류: `extract_topics()` (현재 `data/signals.json` 키워드 매칭) → 텍스트 분류 모델/LLM 호출로 교체
  - 요약 문장: `summarize()` → LLM 생성으로 교체하되, 근거 기록(`evidence`, `change_points`)을 함께 반환하도록 유지
  - 변화 탐지: 이동평균·기간 비교 → 시계열 이상 탐지 모델로 교체
- 서버에서 실행되므로 API 키는 환경변수로 읽으면 브라우저에 노출되지 않습니다. 호출이 느리면 결과를 저장해 두고 화면에서는 저장된 결과를 읽도록 바꾸세요.
- 교사 화면에 보내는 데이터는 반드시 `app/privacy.py`의 `teacher_view()`를 거친 뒤 분석에 넣어야 합니다 (`main.py`의 `teacher_bundle()` 참고).
