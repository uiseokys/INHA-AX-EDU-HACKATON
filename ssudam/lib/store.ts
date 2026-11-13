"use client";

// 브라우저 localStorage 기반의 시연용 상태 저장소.
// 학생 화면과 교사 화면이 같은 저장소를 읽기 때문에, 학생이 보낸 상담 요청이 교사 화면에 나타납니다.
// ⚠️ 시연용 구현입니다. 암호화·접근 제어 등 민감정보 보호 기능은 구현되어 있지 않습니다.

import { useSyncExternalStore } from "react";
import { addDays, todayKey } from "./date";
import type { AppState } from "./types";

const KEY = "ssudam:v1";

let cache: AppState | null = null;
const listeners = new Set<() => void>();

export function createInitialState(today: string): AppState {
  return {
    version: 1,
    todos: [
      { id: "seed-1", text: "수학 수행평가 자료 정리하기", done: true, date: today, kind: "todo" },
      { id: "seed-2", text: "영어 단어 20개 외우기", done: false, date: today, kind: "goal" },
      { id: "seed-3", text: "체육복 챙기기", done: false, date: today, kind: "todo" },
    ],
    myLogs: [],
    skipped: [],
    shareOverrides: {},
    // 시연을 위해 '어제 남긴 회고'를 미리 넣어 둡니다.
    reflections: [
      { date: addDays(today, -1), moments: ["동아리", "수업"], tomorrowGoal: "수학 오답노트 3문제 정리하기" },
    ],
    consent: { trend: false, allNotes: false },
    requests: [],
    caseStatus: {},
    events: {},
    memos: {},
    referrals: [],
  };
}

function read(): AppState {
  if (cache) return cache;
  const initial = createInitialState(todayKey());
  try {
    const raw = window.localStorage.getItem(KEY);
    cache = raw ? { ...initial, ...(JSON.parse(raw) as Partial<AppState>) } : initial;
  } catch {
    cache = initial;
  }
  return cache;
}

function emit() {
  listeners.forEach((l) => l());
}

function onStorage(e: StorageEvent) {
  // 다른 탭(예: 학생 탭 ↔ 교사 탭)에서 바뀐 내용을 반영
  if (e.key === null || e.key === KEY) {
    cache = null;
    emit();
  }
}

function subscribe(listener: () => void) {
  if (listeners.size === 0) window.addEventListener("storage", onStorage);
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) window.removeEventListener("storage", onStorage);
  };
}

export function updateState(fn: (s: AppState) => AppState) {
  cache = fn(read());
  try {
    window.localStorage.setItem(KEY, JSON.stringify(cache));
  } catch {
    // 저장소를 쓸 수 없는 환경에서는 메모리 상태로만 동작
  }
  emit();
}

export function resetState() {
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    // 무시
  }
  cache = null;
  emit();
}

const EMPTY: AppState = createInitialState("1970-01-01");

/**
 * 화면에서 상태를 읽고 바꾸는 훅.
 * 서버 렌더링 중에는 ready=false 이므로, 화면은 ready 가 될 때까지 로딩 상태를 보여 주면 됩니다.
 */
export function useApp() {
  const state = useSyncExternalStore(subscribe, read, () => null);
  const today = useSyncExternalStore(subscribe, todayKey, () => "");
  return {
    ready: state !== null,
    state: state ?? EMPTY,
    today,
    update: updateState,
    reset: resetState,
  };
}

export function newId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}
