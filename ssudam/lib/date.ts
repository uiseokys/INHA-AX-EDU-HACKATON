// 날짜는 모두 'YYYY-MM-DD' 문자열(기기 로컬 기준)로 다룹니다. 문자열 비교로 선후를 판단할 수 있습니다.

const WEEK = ["일", "월", "화", "수", "목", "금", "토"];

export function toKey(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

export function todayKey(): string {
  return toKey(new Date());
}

export function fromKey(key: string): Date {
  const [y, m, d] = key.split("-").map(Number);
  return new Date(y, m - 1, d, 12);
}

export function addDays(key: string, n: number): string {
  const d = fromKey(key);
  d.setDate(d.getDate() + n);
  return toKey(d);
}

export function diffDays(a: string, b: string): number {
  return Math.round((fromKey(a).getTime() - fromKey(b).getTime()) / 86_400_000);
}

export function shortLabel(key: string): string {
  const d = fromKey(key);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export function weekday(key: string): string {
  return WEEK[fromKey(key).getDay()];
}

export function dayLabel(key: string): string {
  return `${shortLabel(key)}(${weekday(key)})`;
}

export function fullLabel(key: string): string {
  const d = fromKey(key);
  return `${d.getMonth() + 1}월 ${d.getDate()}일 ${weekday(key)}요일`;
}

export function relativeLabel(key: string, today: string): string {
  const n = diffDays(today, key);
  if (n === 0) return "오늘";
  if (n === 1) return "어제";
  if (n > 1) return `${n}일 전`;
  return dayLabel(key);
}
