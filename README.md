# 2026 INHA AX-EDU 해커톤 10조

학생 마음 돌봄 웹 프로토타입 모음입니다. 두 프로젝트 모두 Python(FastAPI + Jinja2)으로 만들었고, Python 3.10 이상이 필요합니다.

> **시연용 프로토타입입니다.** 학교·선생님·학생·기관 정보는 모두 합성 데이터이며 실제 정보가 아닙니다.
> 분석 결과는 진단이나 판정이 아닌 참고 정보이고, 로그인·암호화 등 민감정보 보호 기능은 구현되어 있지 않습니다.

| 폴더 | 프로젝트 | 내용 |
| --- | --- | --- |
| [`bokbok/`](bokbok) | **복복복** · 학생 마음 돌봄 플랫폼 | 감정 스티커 기록, AI 챗봇 ‘복복이’(로컬 LLM 연결형), 위험 신호 교사 알림, 상담 예약, 포인트와 우리 반 상점 |
| [`ssudam-py/`](ssudam-py) | **쓰담** · 감정 변화 분석과 지원기관 연계 | 할 일·회고 속 10초 감정 체크인, 근거를 보여 주는 변화 분석, 동의한 정보만 상담교사에게 전달 |

## 복복복 실행

```bash
cd bokbok
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload     # http://localhost:8000
```

챗봇을 로컬 LLM에 연결하려면 `BOKBOK_LLM_MODEL=<모델 이름>` 을 지정해 실행합니다. 지정하지 않으면 미리 써 둔 대답으로 동작합니다.
자세한 내용은 [`bokbok/README.md`](bokbok/README.md)를 참고하세요.

## 쓰담 실행

```bash
cd ssudam-py
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload     # http://localhost:8000
```

자세한 내용은 [`ssudam-py/README.md`](ssudam-py/README.md)를 참고하세요.

## 지키는 원칙

- 감정 분석만으로 학교폭력 피해 여부나 정신건강 상태를 진단하지 않습니다.
- 학생이 공유하지 않은 기록과 챗봇 대화 내용은 선생님 화면에 원문을 보여 주지 않습니다.
- ‘위험 학생’ 같은 낙인 대신 ‘관찰 필요 / 상담 권장’, ‘상담 요청 / 지원 진행 중’처럼 선생님이 할 일 중심으로 표시합니다.
