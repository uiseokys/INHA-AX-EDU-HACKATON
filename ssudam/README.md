# 쓰담 (SSUDAM)

AI 감정 변화 분석 기반 학교폭력 피해학생 조기 발견 및 지원전문기관 연계 서비스 — 2026 INHA AX-EDU 해커톤 시연용 웹 프로토타입

> **시연용 프로토타입입니다.** 학생·학교·기관 정보는 모두 합성 데이터이며, 분석 결과는 진단이나 판정이 아닌 참고 정보입니다.
> 기록은 브라우저 localStorage에만 저장되고, 암호화·접근 제어 같은 민감정보 보호 기능은 구현되어 있지 않습니다.

## 실행

```bash
npm install
npm run dev      # http://localhost:3000
```

```bash
npm run build    # 프로덕션 빌드
npm run test     # 분석·공유 범위 단위 테스트 (vitest)
npm run lint     # ESLint
npm run data     # 합성 감정 기록 재생성 (data/emotion_logs.json, data/emotion_log.csv)
```

## 시연 흐름

1. `/` 에서 **학생으로 시작하기**
2. `/student` 에서 오늘의 할 일 확인 → 감정 이모지 선택 → **기록하기**
3. 같은 화면의 그래프 맨 오른쪽에 오늘 기록이 반영된 것 확인 (`/student/insights` 에서 분석 근거 확인)
4. `/student/support` 에서 **상담 지원 요청 보내기** (공유 범위 선택 가능)
5. `/teacher` 에서 방금 보낸 요청(하늘 · 새 요청) 확인 → 학생 상세
6. **지원기관 찾아보기** → `/teacher/agencies` 에서 유형·지역 선택 → **연결 요청**

화면 아래 **시연 데이터 초기화** 버튼으로 처음 상태로 되돌릴 수 있습니다.

## 폴더 구조

```
app/                      라우트 (서버 컴포넌트 껍데기)
  page.tsx                랜딩
  student/                학생 홈 · insights(마음 분석) · support(도움 요청)
  teacher/                요청 현황 · students/[id](학생 상세) · agencies(지원기관 추천)
components/
  views/                  화면별 클라이언트 컴포넌트
  student/                할 일 · 감정 체크인 · 회고 카드
  charts.tsx              감정 변화 그래프 · 감정 비율 · 추이선 (Recharts)
  insight.tsx             고민 주제 · 변화 시점 · 기록 목록 (근거 표시)
lib/
  analysis.ts             규칙 기반 Mock AI (이동평균 · 기간 비교 · 주제 분류 · 변화 시점)
  privacy.ts              교사 화면에 전달할 기록을 공유 동의 범위로 거르는 함수
  data.ts                 합성 데이터 + 브라우저 상태 조회 함수
  store.ts                localStorage 기반 상태 저장소
  analysis.test.ts        단위 테스트
data/                     합성 데이터 (data/README.md 참고)
scripts/generate-data.mjs 합성 감정 기록 생성 스크립트
```

## 실제 AI 모델을 붙이려면

- **`lib/analysis.ts`의 `analyze()`** 가 유일한 분석 진입점입니다. 입력 `EmotionLog[]`, 출력 `Insight` 형태만 유지하면 화면 코드는 그대로 동작합니다.
  - 주제 분류: `extractTopics()` (현재 `data/signals.json` 키워드 매칭) → 텍스트 분류 모델/LLM 호출로 교체
  - 요약 문장: `summarize()` → LLM 생성으로 교체하되, 근거 기록(`evidence`, `changePoints`)을 함께 반환하도록 유지
  - 변화 탐지: 이동평균·기간 비교 → 시계열 이상 탐지 모델로 교체
- 외부 API를 호출할 때는 키가 브라우저에 노출되지 않도록 `app/api/analyze/route.ts` 같은 서버 라우트를 만들고, 화면에서는 그 라우트를 호출하세요.
- 교사 화면에 보내는 데이터는 반드시 `lib/privacy.ts`의 `teacherView()`를 거친 뒤 분석에 넣어야 합니다.
