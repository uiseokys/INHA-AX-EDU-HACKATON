# 쓰담 시연용 데이터

**이 폴더의 모든 데이터는 시연을 위해 지어낸 합성 데이터입니다. 실제 학생·학교·기관 정보가 아닙니다.**

| 파일 | 내용 |
| --- | --- |
| `students.json` | 가상 학생 8명, 공유 동의 범위, 상담 진행 상태, 초기 상담 요청·기관 연계 내역 |
| `emotion_logs.json` | 학생별 최근 14일 감정 기록 (앱에서 사용). `scripts/generate-data.mjs`로 생성 |
| `emotion_log.csv` | 위 기록과 같은 내용의 CSV (열람·분석용) |
| `signals.json` | 규칙 기반 Mock AI가 쓰는 고민 주제 키워드와 기준값 |
| `agencies.json` | 가상 지원기관 12곳 (Wee클래스·Wee센터·청소년상담복지센터·기타) |

- `dayOffset` / `day_offset`은 오늘을 0으로 한 상대 날짜입니다(-1 = 어제). 앱을 여는 날짜에 맞춰 최근 14일로 변환됩니다.
- `shared` / `shared_with_counselor`는 학생이 그 기록의 메모를 상담교사와 공유하기로 표시했는지를 뜻합니다.
- 감정 기록을 바꾸려면 `scripts/generate-data.mjs`의 시나리오를 수정한 뒤 `npm run data`를 실행하세요.
