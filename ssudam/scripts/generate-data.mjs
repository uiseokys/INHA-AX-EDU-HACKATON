// 쓰담 시연용 합성 감정 기록 생성 스크립트
// 실행: npm run data
// 결과: data/emotion_logs.json (앱에서 사용), data/emotion_log.csv (열람·분석용)
//
// ⚠️ 모든 기록은 시연을 위해 사람이 직접 지어낸 합성 데이터이며, 실제 학생 정보가 아닙니다.
// dayOffset 은 "오늘"을 0으로 한 상대 날짜입니다(-1 = 어제). 앱이 실행되는 날짜 기준으로 변환됩니다.

import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const dataDir = join(dirname(fileURLToPath(import.meta.url)), "..", "data");

// [dayOffset, emotion, intensity(1~5), note, shared(0|1)]
const scenarios = {
  // 시연용 학생 계정(하늘): 최근 1주 사이 또래 관계 고민이 늘어난 흐름. 오늘 기록은 비워 둠.
  S01: [
    [-13, "happy", 4, "동아리에서 새 곡 연습 시작! 재밌었다", 0],
    [-12, "calm", 3, "급식에 좋아하는 메뉴가 나왔다", 0],
    [-11, "happy", 3, "친구들이랑 점심시간에 배드민턴 쳤다", 0],
    [-10, "calm", 3, "", 0],
    [-8, "soso", 3, "수행평가 준비하느라 바빴다", 0],
    [-7, "tired", 3, "모둠 활동 때 내 의견은 그냥 넘어갔다", 0],
    [-6, "anxious", 3, "단톡에서 나만 빼고 약속을 잡은 것 같다", 0],
    [-5, "sad", 3, "점심시간에 혼자 있었다. 친구들이 눈치 주는 느낌", 0],
    [-3, "anxious", 4, "쉬는 시간에 애들이 내 얘기를 하는 것 같아서 눈치 보였다", 0],
    [-2, "sad", 4, "단톡에 올린 말에 아무도 답을 안 했다. 무시당하는 기분", 0],
    [-1, "tired", 3, "잠을 잘 못 잤다. 학교 가기 조금 싫었다", 0],
  ],
  // 대체로 안정적인 기록
  S02: [
    [-13, "happy", 3, "체육 시간 피구에서 우리 팀이 이겼다", 1],
    [-12, "calm", 3, "", 0],
    [-11, "happy", 4, "동아리 발표 준비가 순조롭다", 1],
    [-10, "calm", 2, "", 0],
    [-9, "soso", 2, "비 와서 축 처지는 날", 0],
    [-8, "happy", 3, "급식 떡볶이 최고", 1],
    [-7, "calm", 3, "", 0],
    [-6, "happy", 4, "친구 생일 파티를 준비했다", 1],
    [-5, "calm", 3, "수학 쪽지시험을 무난하게 봤다", 1],
    [-4, "tired", 2, "늦게 자서 피곤", 0],
    [-3, "happy", 3, "", 0],
    [-2, "calm", 4, "주말에 가족이랑 산책", 1],
    [-1, "happy", 4, "발표 칭찬받았다", 1],
    [0, "calm", 3, "", 0],
  ],
  // 학업 스트레스가 반복되는 사례
  S03: [
    [-13, "soso", 3, "중간고사 범위 발표. 양이 너무 많다", 1],
    [-12, "tired", 3, "학원 숙제 끝내니 새벽 1시", 1],
    [-11, "anxious", 3, "수학 모의고사 점수가 또 떨어졌다", 1],
    [-10, "tired", 4, "공부해도 성적이 안 오르는 것 같다", 1],
    [-9, "anxious", 4, "시험 생각하면 배가 아프다", 1],
    [-8, "calm", 2, "상담 선생님이랑 공부 계획을 다시 짰다", 1],
    [-7, "tired", 3, "", 0],
    [-6, "soso", 3, "계획표대로 절반은 했다", 1],
    [-5, "anxious", 3, "영어 수행평가 발표가 걱정된다", 1],
    [-4, "tired", 3, "학원 보충까지 듣고 왔다", 0],
    [-3, "calm", 3, "오답노트 정리하니 조금 마음이 놓인다", 1],
    [-2, "anxious", 3, "시험이 일주일 남았다", 1],
    [-1, "soso", 3, "", 0],
    [0, "tired", 3, "과제가 한꺼번에 몰렸다", 1],
  ],
  // 또래 관계 어려움이 반복되는 사례
  S04: [
    [-13, "calm", 3, "", 0],
    [-12, "happy", 3, "미술 시간이 재밌었다", 1],
    [-11, "soso", 3, "", 0],
    [-10, "calm", 3, "", 0],
    [-9, "soso", 2, "모둠 정할 때 마지막까지 남았다", 1],
    [-8, "sad", 3, "친구들이 내 별명을 부르며 놀렸다", 1],
    [-7, "anxious", 3, "", 0],
    [-6, "sad", 4, "체육 시간에 짝이 없어서 혼자 했다", 1],
    [-5, "anxious", 4, "단톡방에서 내 얘기를 하는 것 같다", 0],
    [-4, "tired", 3, "", 0],
    [-3, "sad", 4, "급식 먹을 때 같이 갈 친구가 없었다", 1],
    [-2, "angry", 3, "내 필통을 숨기고 장난이라고 했다", 1],
    [-1, "sad", 4, "", 0],
    [0, "anxious", 4, "학교 가는 길에 배가 아팠다", 0],
  ],
  // 기록 빈도가 낮아 분석이 어려운 사례
  S05: [
    [-11, "soso", 3, "", 0],
    [-6, "calm", 3, "도서관에서 책을 빌렸다", 1],
    [-2, "tired", 2, "", 0],
  ],
  // 직접 상담 지원을 요청한 사례(그래프 공유 미동의, 일부 기록만 공유)
  S06: [
    [-10, "soso", 3, "", 0],
    [-8, "tired", 3, "", 0],
    [-7, "sad", 3, "말하기 어려운 일이 있었다", 0],
    [-5, "anxious", 4, "", 0],
    [-4, "sad", 4, "누구한테 말해야 할지 모르겠다", 1],
    [-2, "anxious", 4, "", 0],
    [-1, "sad", 3, "선생님께 이야기해보고 싶다", 1],
  ],
  // 진로·가족 고민으로 외부 기관과 연계 중인 사례
  S07: [
    [-13, "anxious", 3, "진로 희망 조사서에 쓸 게 없다", 1],
    [-12, "soso", 3, "", 0],
    [-11, "angry", 3, "엄마랑 고등학교 문제로 다퉜다", 1],
    [-10, "sad", 3, "집에서 말이 안 통하는 느낌", 1],
    [-9, "tired", 3, "", 0],
    [-8, "anxious", 3, "내 꿈이 뭔지 모르겠다", 1],
    [-7, "soso", 3, "", 0],
    [-6, "calm", 3, "진로 상담 받고 조금 정리됐다", 1],
    [-5, "soso", 3, "", 0],
    [-4, "anxious", 2, "아빠가 성적 얘기를 또 꺼냈다", 1],
    [-3, "calm", 3, "센터에서 적성 검사를 예약했다", 1],
    [-2, "happy", 3, "", 0],
    [-1, "calm", 3, "가족이랑 차분하게 얘기해봤다", 1],
    [0, "calm", 4, "", 0],
  ],
  // 공유에 동의하지 않은 사례(교사 화면에 기록이 보이지 않아야 함)
  S08: [
    [-13, "calm", 3, "", 0],
    [-12, "soso", 3, "", 0],
    [-10, "happy", 3, "농구가 재밌었다", 0],
    [-9, "tired", 3, "", 0],
    [-7, "calm", 3, "", 0],
    [-6, "soso", 2, "", 0],
    [-5, "happy", 4, "", 0],
    [-3, "calm", 3, "그냥 평범한 하루", 0],
    [-2, "tired", 2, "", 0],
    [-1, "calm", 3, "", 0],
  ],
};

const logs = Object.entries(scenarios).flatMap(([studentId, rows]) =>
  rows.map(([dayOffset, emotion, intensity, note, shared]) => ({
    studentId,
    dayOffset,
    emotion,
    intensity,
    note,
    shared: shared === 1,
  })),
);

writeFileSync(
  join(dataDir, "emotion_logs.json"),
  JSON.stringify(
    {
      _notice:
        "시연용 합성 데이터입니다. 실제 학생 정보가 아닙니다. scripts/generate-data.mjs 로 생성됩니다.",
      logs,
    },
    null,
    2,
  ) + "\n",
);

const esc = (v) => `"${String(v).replaceAll('"', '""')}"`;
const csv = [
  "student_id,day_offset,emotion,intensity,note,shared_with_counselor",
  ...logs.map((l) =>
    [l.studentId, l.dayOffset, l.emotion, l.intensity, esc(l.note), l.shared ? 1 : 0].join(","),
  ),
].join("\n");
writeFileSync(join(dataDir, "emotion_log.csv"), csv + "\n");

console.log(`합성 감정 기록 ${logs.length}건 생성 완료 → data/emotion_logs.json, data/emotion_log.csv`);
