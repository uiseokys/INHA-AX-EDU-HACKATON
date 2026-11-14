# 감정 휠 + 강도 다이얼 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 복복복 감정 기록 화면(`/student/record`)을 원형 감정 휠로 바꾸고, 강도(1~5)를 함께 기록·표시한다.

**Architecture:** 기존 라디오·체크박스 폼을 그대로 두고 CSS(`:has()`, `cos()/sin()`, 컨테이너 단위)로 원형 배치와 전환을 만든다. 강도 값은 `<input type="range" name="intensity">`가 갖고, 스크립트는 그 위에 끌 수 있는 고리(다이얼)만 덧씌운다. 서버는 기록에 `intensity` 한 값을 더 저장한다.

**Tech Stack:** FastAPI · Jinja2 · Tailwind CSS v4(`scripts/build_css.sh`) · 순수 JS(`app/static/app.js`) · pytest

**Spec:** `docs/superpowers/specs/2026-11-14-emotion-wheel-design.md`

## Global Constraints

- 모든 경로는 `bokbok/` 기준. 테스트는 `bokbok/.venv/bin/pytest`.
- 색·스티커·복복이·글꼴·`BTN`/`CARD`/`CHIP`/`FIELD` 스타일은 바꾸지 않는다. 감정은 5종, 감정 단어도 그대로.
- 스크립트가 꺼져도 스티커·단어·강도·문장을 골라 기록할 수 있어야 한다.
- 분석·알림 규칙(`analysis.py`, `chatbot.py`)은 건드리지 않는다.
- 문구는 기존 화면과 같은 해요체.
- 템플릿·Python의 클래스를 바꾼 뒤에는 `./scripts/build_css.sh`로 `app/static/app.css`를 다시 만든다.
- 커밋은 사용자가 요청할 때만 한다 (작업 브랜치: `feat/emotion-wheel`).

## Review Focus

1. **강도 값이 이상할 때** (`"abc"`, `""`, `"0"`, `"9"`): 오류 화면 없이 기록되고 1~5로 잘리거나 비어야 한다 → Task 1 테스트.
2. **강도 없이 저장된 예전 기록** (`var/state.json`의 기존 `my_records`, 합성 과거 기록): 학생 홈·리포트·선생님 화면이 그대로 열려야 한다 → Task 1 테스트.
3. **오늘 기록을 다시 고칠 때**: 전에 고른 강도가 다이얼에 그대로 보여야 한다 → Task 1 테스트.
4. **휴대폰에서 손가락으로 돌릴 때**: 화면이 같이 스크롤되지 않고 다이얼이 움직여야 한다 → Task 3 브라우저 확인(모바일 390px).
5. **좁은 화면의 긴 단어** (‘눈치 보이는’, ‘자랑스러운’): 단어끼리 겹치거나 카드 밖으로 잘리지 않아야 한다 → Task 2 브라우저 확인(390px, 불안·기쁨).

---

### Task 1: 강도 저장과 표시

**Files:**
- Modify: `app/models.py` (`Record`, 새 상수), `app/main.py` (`save_record`, 템플릿 전역), `app/templates/_ui.html` (새 매크로), `app/templates/student_home.html`, `app/templates/student_report.html`, `app/templates/teacher_student.html`
- Test: `tests/test_app.py`

**Interfaces:**
- Produces: `Record.intensity: int | None = None` · `models.INTENSITY_LABELS: dict[int, str]` = `{1: "아주 조금", 2: "조금", 3: "보통", 4: "많이", 5: "아주 많이"}` (템플릿 전역 이름 `INTENSITY`) · `main.parse_intensity(raw: str) -> int | None` · 폼 필드 `intensity` · 매크로 `ui.intensity(n)` (값이 없으면 아무것도 그리지 않음, 있으면 `강도 n` 글자를 포함)

- [ ] **Step 1: 실패하는 테스트 작성** (`tests/test_app.py`, `import re` 추가)

```python
def test_record_saves_and_shows_intensity(client):
    onboard(client)
    client.post("/student/record", data={"emotion": "sad", "words": ["속상한"], "intensity": "4"})
    assert store.load()["my_records"][-1]["intensity"] == 4
    for path in ["/student", "/student/report", f"/teacher/students/{data.ME_ID}"]:
        assert "강도 4" in client.get(path).text, path


@pytest.mark.parametrize("raw, saved", [("3", 3), ("0", 1), ("9", 5), ("abc", None), ("", None)])
def test_record_intensity_is_clamped(client, raw, saved):
    onboard(client)
    res = client.post("/student/record", data={"emotion": "joy", "intensity": raw}, follow_redirects=False)
    assert res.status_code == 303
    assert store.load()["my_records"][-1]["intensity"] == saved


def test_old_record_without_intensity_still_renders(client):
    onboard(client)
    client.post("/student/record", data={"emotion": "sad"})
    with store.editing() as state:
        state["my_records"][-1].pop("intensity")
    for path in ["/student", "/student/record", "/student/report", f"/teacher/students/{data.ME_ID}"]:
        assert client.get(path).status_code == 200, path
    assert "강도 " not in client.get("/student").text


def test_record_page_prefills_intensity(client):
    onboard(client)
    client.post("/student/record", data={"emotion": "sad", "intensity": "5"})
    assert re.search(r'name="intensity"[^>]*value="5"', client.get("/student/record").text)
```

(리다이렉트 상태 코드는 `back()`이 쓰는 값에 맞춘다.)

- [ ] **Step 2: 실패 확인** — `.venv/bin/pytest tests/test_app.py -k intensity -q` → 새 테스트 FAIL
- [ ] **Step 3: 구현** — `Record`에 필드, `parse_intensity`(숫자가 아니면 `None`, 아니면 1~5로 자름), `save_record`에 `intensity: Annotated[str, Form()] = ""`를 받아 저장, `INTENSITY` 전역 등록, `ui.intensity(n)` 매크로, 세 화면에 표시(홈: 오늘 기록 카드의 단어 칩 옆 / 리포트·선생님 상세: 최근 기록 줄의 단어 뒤 `· 강도 n`).
- [ ] **Step 4: 통과 확인** — `.venv/bin/pytest -q` → 전체 PASS

### Task 2: 감정 휠 배치·애니메이션·문구

**Files:**
- Modify: `app/templates/student_record.html` (전체 다시 구성), `app/static/src/input.css` (`wheel-*` 스타일과 키프레임), `app/main.py` (`SHOW_WORDS` 제거), `app/static/app.css` (빌드 결과)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `INTENSITY`, 폼 필드 `intensity`, `existing.intensity`
- Produces (Task 3이 씀): `form[data-wheel]` · `.wheel`(휠 무대) · `.wheel-dial`(고리, CSS 변수 `--level`) · `[data-dial-handle]` · `[data-dial-arc]` · `[data-dial-text]` · `input[name=intensity]` · `button[data-wheel-reset]`. 폼에 `data-dial-ready`가 붙으면 고리가 보이고 슬라이더는 화면에서만 숨는다.

정해 둔 값:
- 무대: 정사각형, 최대 너비 400px, `container-type: inline-size`. 좁은 화면에서는 카드 안쪽 여백만큼 양옆으로 넓힌다.
- 스티커 노드 5개: 반지름 `34cqw`, 각도 `72° × i − 90°`, 흰 원판 + 스티커 + 이름. 처음 열릴 때 가운데에서 차례로 퍼짐(`wheel-in`, 60ms 간격).
- 가운데: 복복이(`happy`, 둥실 떠 있는 `animate-float`). 스티커를 고르면 사라짐.
- 선택: 고른 노드는 가운데로 이동·1.1배·테두리 `e.deep`, 나머지는 0.5배로 줄며 사라짐. 전환 `0.6s cubic-bezier(0.22, 1, 0.36, 1)`.
- 단어 칩 8개: 타원 `rx 36cqw / ry 42cqw`, 각도 `45° × k + 22.5°`, 35ms 간격으로 튀어나옴(`cubic-bezier(0.34, 1.45, 0.64, 1)`). 고르면 배경 `e.color`, 테두리 `e.deep`.
- 고리: 지름 `38cqw`, 점선 궤도 + 5칸 눈금(72° 간격, 1이 맨 위, 시계 방향) + 채워지는 호 + 숫자 손잡이. 색은 고른 감정의 `e.deep`.
- 문구:
  - 알약: `오늘의 감정 기록 · {{ today | full_label }}`
  - 고르기 전: `오늘 마음은 어땠나요?` / `가장 가까운 스티커를 눌러 보세요.`
  - 고른 뒤: `‘{{ e.label }}’에 가까운 마음을 골라 주세요` / `고리를 돌려 얼마나 그랬는지 정하고, 딱 맞는 단어를 눌러 보세요.`
  - 강도 줄: `얼마나 그랬나요?` + `강도 n · {{ INTENSITY[n] }}`
  - 되돌리기: `다시 고르기`
  - 버튼: `스티커를 먼저 골라 주세요` → `기록하고 포인트 받기`
  - 스위치 설명: `끄면 나만 볼 수 있어요. 스티커와 감정 단어, 강도는 선생님 리포트에 쓰여요.`
- 문장 입력·스위치·안내 카드는 스티커를 고르면 `animate-fade-up`으로 나타난다. `1 / 3` 같은 단계 표시는 없앤다.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_record_page_is_emotion_wheel(client):
    onboard(client)
    page = client.get("/student/record").text
    assert "오늘 마음은 어땠나요?" in page and "가장 가까운 스티커를 눌러 보세요." in page
    assert "‘슬픔’에 가까운 마음을 골라 주세요" in page
    assert page.count('name="emotion"') == 5 and page.count('name="words"') == 40
    assert re.search(r'name="intensity"[^>]*value="3"', page)
    assert "다시 고르기" in page and "기록하고 포인트 받기" in page
    assert "강도는 선생님 리포트에 쓰여요" in page


def test_record_page_preselects_sticker_from_home(client):
    onboard(client)
    assert re.search(r'id="emo-sad"[^>]*checked', client.get("/student/record?e=sad").text)
```

- [ ] **Step 2: 실패 확인** — `.venv/bin/pytest tests/test_app.py -k record_page -q`
- [ ] **Step 3: 템플릿과 스타일 구현**, `./scripts/build_css.sh` 실행
- [ ] **Step 4: 통과 확인** — `.venv/bin/pytest -q` → 전체 PASS
- [ ] **Step 5: 브라우저 확인** — `http://localhost:8020/student/record`를 데스크톱과 모바일(390px)에서 열어 다섯 감정을 각각 골라 본다. 불안·기쁨에서 긴 단어가 겹치거나 잘리지 않는지, `?e=sad`로 들어오면 처음부터 가운데에 있는지 확인.

### Task 3: 강도 다이얼 동작

**Files:**
- Modify: `app/static/app.js` (`// 7) 감정 휠` 절 추가)

**Interfaces:**
- Consumes: Task 2의 Produces 전부

동작:
- 시작할 때 폼에 `data-dial-ready`를 붙이고 `input[name=intensity]`의 값으로 고리를 맞춘다.
- `setLevel(n)`: 슬라이더 값, `.wheel-dial`의 `--level`, 호 길이, 손잡이 숫자, `강도 n · 말`을 함께 바꾼다.
- 고리 위에서 `pointerdown`/`pointermove`(포인터 캡처): 무대 중심에서 본 각도(위쪽 0°, 시계 방향)로 `level = round(각도 / 72) % 5 + 1`.
- 슬라이더의 `input` 이벤트(키보드 화살표)도 `setLevel`로 이어진다.
- `다시 고르기`: 감정·단어 선택을 모두 풀고 강도를 3으로 되돌린다.

- [ ] **Step 1: 구현**
- [ ] **Step 2: 브라우저 확인** — 모바일 390px과 데스크톱에서: 손잡이를 끌어 1→5, 눈금을 눌러 이동, 키보드 화살표로 이동, `다시 고르기` 뒤 3으로 복귀, 강도 4로 기록한 뒤 홈에 `강도 4`가 보이는지, 다시 기록 화면에 들어오면 4로 맞춰져 있는지. 콘솔 오류 없음.
- [ ] **Step 3: 전체 테스트** — `.venv/bin/pytest -q` → 전체 PASS
