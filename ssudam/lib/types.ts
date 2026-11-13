export type EmotionId = "happy" | "calm" | "soso" | "tired" | "anxious" | "sad" | "angry";

/** 감정 기록 한 건. date 는 'YYYY-MM-DD' (기기 로컬 날짜) */
export interface EmotionLog {
  id: string;
  studentId: string;
  date: string;
  emotion: EmotionId;
  intensity: number; // 1~5
  note?: string;
  /** 학생이 이 기록의 메모를 상담교사와 공유하기로 표시했는지 */
  shared: boolean;
}

/** 학생이 상담교사에게 허용한 공유 범위 */
export interface Consent {
  /** 감정 변화 그래프(이모지·강도) 공유 */
  trend: boolean;
  /** 개별 표시와 무관하게 모든 메모 공유 */
  allNotes: boolean;
}

/** 지원 절차 중심의 진행 상태 (위험도 판정이 아님) */
export type CaseStatus = "none" | "requested" | "review" | "in_progress" | "referred" | "closed";

export interface Student {
  id: string;
  name: string;
  grade: number;
  classNo: number;
  avatar: string;
  scenario: string;
  consent: Consent;
  caseStatus: CaseStatus;
  statusNote?: string;
}

export interface SupportRequest {
  id: string;
  studentId: string;
  date: string;
  topic: string;
  message: string;
  preferred: string;
}

export interface Referral {
  id: string;
  studentId: string;
  agencyId: string;
  date: string;
  note: string;
}

export interface Todo {
  id: string;
  text: string;
  done: boolean;
  date: string;
  kind: "todo" | "goal";
}

export interface Reflection {
  date: string;
  moments: string[];
  tomorrowGoal: string;
  /** 다음 접속 때 학생이 확인한 결과 */
  goalResult?: "done" | "carried";
}

export interface Agency {
  id: string;
  name: string;
  type: string;
  region: string;
  summary: string;
  description: string;
  services: string[];
  topics: string[];
  hours: string;
  mode: string[];
}

export interface StatusEvent {
  date: string;
  text: string;
}

/** 브라우저 localStorage 에 저장되는 시연용 상태 */
export interface AppState {
  version: 1;
  todos: Todo[];
  /** 시연용 학생(하늘)이 직접 남긴 감정 기록 */
  myLogs: EmotionLog[];
  /** 체크인을 건너뛴 날짜 */
  skipped: string[];
  /** 기록별 공유 여부 변경 (기록 id → 공유 여부) */
  shareOverrides: Record<string, boolean>;
  reflections: Reflection[];
  consent: Consent;
  requests: SupportRequest[];
  caseStatus: Record<string, CaseStatus>;
  events: Record<string, StatusEvent[]>;
  memos: Record<string, string>;
  referrals: Referral[];
}
