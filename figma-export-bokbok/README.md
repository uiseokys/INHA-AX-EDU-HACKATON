# 복복복 · Figma 작업용 화면 자료

복복복 웹 프로토타입(`bokbok`)의 현재 디자인을 Figma에서 작업할 수 있도록 내보낸 자료입니다.
화면 속 학교·선생님·학생 정보는 모두 시연용 합성 데이터입니다.
실제 사이트: https://bokbok-51gl.onrender.com (무료 서버라 첫 접속이 1분 가까이 걸릴 수 있어요)

| 폴더 | 내용 | Figma에서 쓰는 법 |
| --- | --- | --- |
| `assets/` | **복복이 캐릭터 3종, 감정 스티커 5종 SVG** | Figma에 끌어다 놓으면 **편집 가능한 벡터**가 됩니다. 색·모양을 바로 고칠 수 있어요 |
| `screens/` | 화면별 PNG. 데스크톱 1440px, 모바일 390px | 캔버스에 끌어다 놓고 참고·트레이싱용으로 사용 |
| `html/` | 화면별 단독 HTML (CSS 포함) | 화면 전체를 편집 가능한 레이어로 바꾸고 싶을 때 사용 (아래 참고) |
| `tokens/tokens.json` | 색·감정 색·학생 상태 칩·글자·모서리·그림자·레이아웃 값 (W3C Design Tokens 형식) | Tokens Studio 같은 토큰 플러그인으로 불러오기 |
| `tokens/token-sheet.png` | 캐릭터·스티커·색·글자를 한 장에 정리한 기준표 | 캔버스에 스타일 기준으로 배치 |
| `manifest.json` | 화면 이름·주소·파일 목록 | 참고용 |

- 모바일 화면 중 세로가 4096px을 넘는 것은 `-part1`, `-part2`로 나눠 저장했습니다. Figma가 한 변이 4096px을 넘는 이미지를 자동으로 축소하기 때문입니다.
- 글꼴은 **Pretendard**입니다. 같은 모양으로 작업하려면 Pretendard를 설치해 주세요.
- 아이콘은 **Lucide** 아이콘입니다. Figma의 Lucide 플러그인에서 같은 아이콘을 찾을 수 있어요 (예: house, chart-column, message-circle-more, store, life-buoy).
- 감정 스티커 5색은 기획서 15쪽의 색상(기쁨 #FFD66B, 평온 #A9DCC5, 슬픔 #AFC9EE, 불안 #C8B5E8, 분노 #F2A49B)을 그대로 썼습니다.

## 화면 목록

| 파일 | 화면 | 코드에서 고칠 파일 (`bokbok/app/templates/`) |
| --- | --- | --- |
| `01-landing` | 처음 화면 | `landing.html` |
| `02-student-welcome` | 학생 · 처음 접속 기본 정보 입력 | `student_welcome.html` |
| `03-student-home` | 학생 홈 · 기록 전 | `student_home.html` |
| `04-student-record` | 감정 기록 · 스티커와 단어 고르기 | `student_record.html` |
| `05-student-record-saved` | 기록 완료 · 포인트 적립과 복복이 권유 창 | `student_home.html` (아래쪽 overlay) |
| `06-student-home-recorded` | 학생 홈 · 기록 후 | `student_home.html` |
| `07-student-report` | 나의 감정 리포트 | `student_report.html` |
| `08-student-chat` | 복복이 대화 | `student_chat.html`, `_chat_messages.html` |
| `09-student-chat-safety` | 복복이 · 위험 신호 안전 안내 | `_chat_messages.html` |
| `10-student-help` | 도움이 필요할 때 | `student_help.html` |
| `11-student-help-detail` | 도움 상세 · 학교폭력 | `student_help_detail.html` |
| `12-student-counsel` | 상담 신청 | `student_counsel.html` |
| `13-student-shop` | 우리 반 복복 상점 | `student_shop.html` |
| `14-student-points` | 내 포인트 | `student_points.html` |
| `15-teacher-home` | 선생님 · 월간 정서 현황 (상단 고정 알림) | `teacher_home.html` |
| `16-teacher-student` | 선생님 · 학생 상세 리포트 | `teacher_student.html` |
| `17-teacher-alerts` | 선생님 · 알림 (카톡 공지 형식) | `teacher_alerts.html` |
| `18-teacher-counsel` | 선생님 · 상담 일정 | `teacher_counsel.html` |
| `19-teacher-shop` | 선생님 · 상점 관리 | `teacher_shop.html` |
| `20-teacher-shop-edit` | 선생님 · 상품 추가 | `teacher_shop.html` |

- 상단 메뉴·모바일 하단 탭은 `layout.html`, 복복이 캐릭터·감정 스티커·그래프·달력·전화 버튼 같은 공통 요소는 `_ui.html`에 있습니다.
- 색과 글꼴은 `bokbok/app/static/src/input.css`, 버튼·카드 공통 스타일은 `bokbok/app/main.py`의 `BTN`, `CARD`에 있습니다.
- 전화 걸기 확인 창(1388 등)은 버튼을 눌러야 뜨는 창이라 캡처에 없습니다. 실제 사이트의 ‘도움’ 화면에서 확인해 주세요.

## 편집 가능한 레이어로 바꾸려면

PNG는 이미지라서 글자나 색을 바로 고칠 수 없습니다. 화면 전체를 레이어로 쓰고 싶다면 HTML을 Figma 레이어로 바꿔 주는 외부 플러그인(예: html.to.design)을 사용할 수 있습니다.

- **가장 쉬운 방법**: 플러그인의 ‘URL로 가져오기’에 실제 사이트 주소(https://bokbok-51gl.onrender.com/…)를 넣습니다. 다만 학생 화면은 처음 접속하면 기본 정보 입력으로 넘어가는 등 상태에 따라 달라지므로, 원하는 상태가 그대로 담긴 `html/` 파일을 쓰는 편이 정확합니다.
- **`html/` 파일 쓰기**: Chrome에서 파일을 연 뒤 플러그인의 Chrome 확장 프로그램으로 지금 보는 화면을 가져옵니다. 확장 프로그램이 로컬 파일을 읽으려면 Chrome 확장 설정에서 “파일 URL에 대한 액세스 허용”을 켜야 할 수 있습니다.

플러그인 사용법과 요금은 해당 서비스의 안내를 따르세요. 변환 결과는 원본과 조금 다를 수 있습니다.

## 디자인을 코드에 반영하는 방법

Figma에서 수정한 화면의 **프레임 링크**(프레임 우클릭 → Copy link)를 Claude에게 전달하면, 그 디자인을 보고 `bokbok` 코드에 반영할 수 있습니다. 이를 위해 Claude 쪽에 Figma 연결이 되어 있어야 합니다.
캐릭터·스티커를 고쳤다면 수정한 SVG 파일을 함께 주세요.

## 다시 내보내기

화면을 고친 뒤 자료를 새로 만들려면 `bokbok/scripts/export_for_figma.py` 맨 위 설명을 따라 실행하세요. (Google Chrome, Pillow, Jinja2 필요)
