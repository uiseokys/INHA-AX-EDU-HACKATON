import type { Consent, EmotionLog } from "./types";

export interface TeacherView {
  /** 교사에게 보여도 되는 기록 (공유하지 않은 메모는 제거됨) */
  logs: EmotionLog[];
  /** 감정 변화 그래프 공유에 동의했는지 */
  trendVisible: boolean;
  /** 메모까지 볼 수 있는 기록 수 */
  sharedNoteCount: number;
}

/**
 * 상담교사 화면에 전달할 기록을 걸러냅니다.
 * 교사 화면은 반드시 이 함수를 거친 기록만 사용해야 합니다.
 *
 * - 메모: 학생이 그 기록을 공유로 표시했거나, 전체 메모 공유에 동의한 경우에만 포함
 * - 감정·강도: 그래프 공유에 동의한 경우 전체 포함, 아니면 공유된 기록만 포함
 */
export function teacherView(logs: EmotionLog[], consent: Consent): TeacherView {
  const noteVisible = (l: EmotionLog) => l.shared || consent.allNotes;
  const visible = logs
    .filter((l) => consent.trend || l.shared || (consent.allNotes && !!l.note))
    .map((l) => ({ ...l, note: noteVisible(l) ? l.note : undefined }));
  return {
    logs: visible,
    trendVisible: consent.trend,
    sharedNoteCount: visible.filter((l) => !!l.note).length,
  };
}
