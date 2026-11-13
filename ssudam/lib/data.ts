// 합성 데이터(data/*.json)와 브라우저 상태(AppState)를 합쳐 화면에 필요한 형태로 꺼내는 함수 모음

import agenciesFile from "@/data/agencies.json";
import logsFile from "@/data/emotion_logs.json";
import signals from "@/data/signals.json";
import studentsFile from "@/data/students.json";
import { addDays } from "./date";
import type {
  Agency,
  AppState,
  CaseStatus,
  Consent,
  EmotionId,
  EmotionLog,
  Referral,
  Student,
  SupportRequest,
} from "./types";

/** 학생 모드에서 사용하는 시연용 계정 */
export const ME_ID = "S01";

export const SCHOOL = studentsFile.school;
export const students = studentsFile.students as Student[];
export const agencies = agenciesFile.agencies as Agency[];
export const agencyTypes = agenciesFile.types;
export const regions = agenciesFile.regions;
export const topicDefs = signals.topics;

export function getStudent(id: string): Student | undefined {
  return students.find((s) => s.id === id);
}

export function getAgency(id: string): Agency | undefined {
  return agencies.find((a) => a.id === id);
}

export function agencyTypeLabel(type: string): string {
  return agencyTypes.find((t) => t.id === type)?.label ?? type;
}

export function topicLabel(id: string): string {
  return topicDefs.find((t) => t.id === id)?.label ?? id;
}

/** 합성 기록의 상대 날짜(dayOffset)를 오늘 기준 실제 날짜로 변환 */
export function seedLogs(studentId: string, today: string): EmotionLog[] {
  return logsFile.logs
    .filter((r) => r.studentId === studentId)
    .map((r) => ({
      id: `${r.studentId}:${addDays(today, r.dayOffset)}`,
      studentId: r.studentId,
      date: addDays(today, r.dayOffset),
      emotion: r.emotion as EmotionId,
      intensity: r.intensity,
      note: r.note || undefined,
      shared: r.shared,
    }));
}

/** 한 학생의 전체 기록. 시연용 학생은 직접 남긴 기록과 공유 설정 변경을 반영 */
export function logsFor(studentId: string, state: AppState, today: string): EmotionLog[] {
  const base = seedLogs(studentId, today);
  if (studentId !== ME_ID) return base;
  const byDate = new Map(base.map((l) => [l.date, l]));
  for (const l of state.myLogs) byDate.set(l.date, l);
  return [...byDate.values()]
    .map((l) => (l.id in state.shareOverrides ? { ...l, shared: state.shareOverrides[l.id] } : l))
    .sort((a, b) => a.date.localeCompare(b.date));
}

export function consentFor(student: Student, state: AppState): Consent {
  return student.id === ME_ID ? state.consent : student.consent;
}

export function statusFor(student: Student, state: AppState): CaseStatus {
  return state.caseStatus[student.id] ?? student.caseStatus;
}

export function requestsFor(studentId: string, state: AppState, today: string): SupportRequest[] {
  const seeded = studentsFile.seedRequests
    .filter((r) => r.studentId === studentId)
    .map(({ dayOffset, ...r }) => ({ ...r, date: addDays(today, dayOffset) }));
  return [...seeded, ...state.requests.filter((r) => r.studentId === studentId)].sort((a, b) =>
    b.date.localeCompare(a.date),
  );
}

export function referralsFor(studentId: string, state: AppState, today: string): Referral[] {
  const seeded = studentsFile.seedReferrals
    .filter((r) => r.studentId === studentId)
    .map(({ dayOffset, ...r }) => ({ ...r, date: addDays(today, dayOffset) }));
  return [...seeded, ...state.referrals.filter((r) => r.studentId === studentId)].sort((a, b) =>
    b.date.localeCompare(a.date),
  );
}

export interface AgencyMatch {
  agency: Agency;
  /** 학생의 반복 주제와 겹치는 기관 지원 주제 */
  matchedTopics: string[];
}

/** 조건(유형·지역)에 맞는 기관을 고르고, 학생의 고민 주제와 겹치는 기관을 앞에 배치 */
export function matchAgencies(
  list: Agency[],
  filter: { type: string; region: string },
  studentTopics: string[] = [],
): AgencyMatch[] {
  return list
    .filter((a) => (filter.type === "all" || a.type === filter.type) && (filter.region === "all" || a.region === filter.region))
    .map((agency) => ({ agency, matchedTopics: agency.topics.filter((t) => studentTopics.includes(t)) }))
    .sort((a, b) => b.matchedTopics.length - a.matchedTopics.length);
}
