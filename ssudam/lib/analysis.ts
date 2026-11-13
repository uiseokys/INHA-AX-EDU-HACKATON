// ─────────────────────────────────────────────────────────────────────────────
// 쓰담 감정 기록 분석 (규칙 기반 Mock AI)
//
// 실제 AI 모델을 붙일 때는 이 파일의 `analyze()`만 교체하면 됩니다.
// 입력(EmotionLog[])과 출력(Insight) 형태를 유지하면 화면 코드는 그대로 동작합니다.
//
// 이 분석은 학생의 자기 이해를 돕는 참고 정보이며,
// 학교폭력 피해 여부나 정신건강 상태를 진단·판정하지 않습니다.
// ─────────────────────────────────────────────────────────────────────────────

import signals from "@/data/signals.json";
import { addDays, dayLabel, shortLabel } from "./date";
import { EMOTIONS, EMOTION_LIST } from "./emotions";
import type { EmotionId, EmotionLog } from "./types";

const RULES = signals.rules;

export interface SeriesPoint {
  date: string;
  label: string;
  /** 마음 점수 1(무거움)~5(가벼움). 기록이 없는 날은 null */
  score: number | null;
  /** 최근 기록 3건 이동평균 */
  avg: number | null;
  emotion?: EmotionId;
  intensity?: number;
  note?: string;
}

export interface TopicEvidence {
  date: string;
  emotion: EmotionId;
  note: string;
  matched: string[];
}

export interface TopicResult {
  id: string;
  label: string;
  emoji: string;
  count: number;
  evidence: TopicEvidence[];
}

export interface ChangePoint {
  date: string;
  kind: "shift" | "jump";
  /** shift: 이전 기간 평균 대비 이동평균 차이 / jump: 직전 기록 대비 차이 */
  delta: number;
  description: string;
  log: { emotion: EmotionId; intensity: number; note?: string };
}

export interface Insight {
  days: number;
  recordCount: number;
  minRecords: number;
  /** 분석에 필요한 최소 기록 수를 채웠는지 */
  enough: boolean;
  series: SeriesPoint[];
  ratio: { emotion: EmotionId; count: number; pct: number }[];
  change: {
    prevAvg: number | null;
    recentAvg: number | null;
    diff: number | null;
    direction: "up" | "down" | "steady" | "unknown";
  };
  topics: TopicResult[];
  changePoints: ChangePoint[];
}

const round1 = (n: number) => Math.round(n * 10) / 10;
const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;

/** 감정 종류와 강도를 1~5점의 '마음 점수'로 환산 (3 = 보통) */
export function moodScore(log: Pick<EmotionLog, "emotion" | "intensity">): number {
  const raw = 3 + EMOTIONS[log.emotion].valence * log.intensity * 0.4;
  return round1(Math.min(5, Math.max(1, raw)));
}

/** 최근 N일을 하루 단위로 펼친 그래프용 데이터 (+ 이동평균) */
export function buildSeries(logs: EmotionLog[], today: string, days = 14): SeriesPoint[] {
  const byDate = new Map(logs.map((l) => [l.date, l]));
  const recent: number[] = [];
  const out: SeriesPoint[] = [];
  for (let i = days - 1; i >= 0; i--) {
    const date = addDays(today, -i);
    const log = byDate.get(date);
    if (!log) {
      out.push({ date, label: shortLabel(date), score: null, avg: null });
      continue;
    }
    const score = moodScore(log);
    recent.push(score);
    out.push({
      date,
      label: shortLabel(date),
      score,
      avg: round1(mean(recent.slice(-RULES.movingAverageWindow))),
      emotion: log.emotion,
      intensity: log.intensity,
      note: log.note,
    });
  }
  return out;
}

/** 마음이 무거웠던 날의 메모에서 키워드로 고민 주제를 분류 */
export function extractTopics(logs: EmotionLog[]): TopicResult[] {
  const heavy = logs.filter((l) => l.note && EMOTIONS[l.emotion].valence <= 0);
  return signals.topics
    .map((t) => {
      const evidence = heavy
        .map((l) => ({
          date: l.date,
          emotion: l.emotion,
          note: l.note as string,
          matched: t.keywords.filter((k) => (l.note as string).includes(k)),
        }))
        .filter((e) => e.matched.length > 0)
        .sort((a, b) => b.date.localeCompare(a.date));
      return { id: t.id, label: t.label, emoji: t.emoji, count: evidence.length, evidence };
    })
    .filter((t) => t.count > 0)
    .sort((a, b) => b.count - a.count);
}

export function analyze(allLogs: EmotionLog[], today: string, days = 14): Insight {
  const start = addDays(today, -(days - 1));
  const logs = allLogs
    .filter((l) => l.date >= start && l.date <= today)
    .sort((a, b) => a.date.localeCompare(b.date));

  const series = buildSeries(logs, today, days);
  const points = series.filter((p) => p.score !== null) as (SeriesPoint & { score: number; avg: number })[];

  // 1) 감정별 기록 비율
  const ratio = EMOTION_LIST.map((e) => {
    const count = logs.filter((l) => l.emotion === e.id).length;
    return { emotion: e.id, count, pct: logs.length ? Math.round((count / logs.length) * 100) : 0 };
  })
    .filter((r) => r.count > 0)
    .sort((a, b) => b.count - a.count);

  // 2) 이전 기간 vs 최근 기간 평균 비교
  const recentStart = addDays(today, -(RULES.periodDays - 1));
  const prev = points.filter((p) => p.date < recentStart).map((p) => p.score);
  const recent = points.filter((p) => p.date >= recentStart).map((p) => p.score);
  const prevAvg = prev.length >= 2 ? round1(mean(prev)) : null;
  const recentAvg = recent.length >= 2 ? round1(mean(recent)) : null;
  const diff = prevAvg !== null && recentAvg !== null ? round1(recentAvg - prevAvg) : null;
  const direction =
    diff === null
      ? "unknown"
      : diff <= -RULES.changeThreshold
        ? "down"
        : diff >= RULES.changeThreshold
          ? "up"
          : "steady";

  // 3) 변화가 나타난 날짜와 그날의 기록
  const changePoints: ChangePoint[] = [];
  if (prevAvg !== null && (direction === "down" || direction === "up")) {
    const sign = direction === "down" ? -1 : 1;
    const shift = points.find(
      (p, i) => i >= 2 && (p.avg - prevAvg) * sign >= RULES.changeThreshold,
    );
    if (shift) {
      changePoints.push({
        date: shift.date,
        kind: "shift",
        delta: round1(shift.avg - prevAvg),
        description: `최근 기록 3건의 평균(${shift.avg}점)이 이전 기간 평균(${prevAvg}점)과 ${Math.abs(round1(shift.avg - prevAvg))}점 벌어지기 시작한 날`,
        log: { emotion: shift.emotion!, intensity: shift.intensity!, note: shift.note },
      });
    }
  }
  const jumps = points
    .map((p, i) => (i === 0 ? null : { p, delta: round1(p.score - points[i - 1].score), from: points[i - 1] }))
    .filter((j): j is NonNullable<typeof j> => j !== null && Math.abs(j.delta) >= RULES.jumpThreshold)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
    .slice(0, 2);
  for (const j of jumps) {
    if (changePoints.some((c) => c.date === j.p.date)) continue;
    changePoints.push({
      date: j.p.date,
      kind: "jump",
      delta: j.delta,
      description: `직전 기록(${dayLabel(j.from.date)}, ${j.from.score}점)보다 ${Math.abs(j.delta)}점 ${j.delta < 0 ? "낮아진" : "높아진"} 날`,
      log: { emotion: j.p.emotion!, intensity: j.p.intensity!, note: j.p.note },
    });
  }
  changePoints.sort((a, b) => a.date.localeCompare(b.date));

  return {
    days,
    recordCount: logs.length,
    minRecords: RULES.minRecordsForAnalysis,
    enough: logs.length >= RULES.minRecordsForAnalysis,
    series,
    ratio,
    change: { prevAvg, recentAvg, diff, direction },
    topics: extractTopics(logs),
    changePoints,
  };
}

/** 분석 결과를 문장으로 정리. tone: 학생용(친근) / 교사용(업무) */
export function summarize(insight: Insight, tone: "student" | "teacher"): string[] {
  const s = tone === "student";
  const lines: string[] = [];
  if (!insight.enough) {
    lines.push(
      s
        ? `최근 ${insight.days}일 동안 기록이 ${insight.recordCount}건이라 아직 흐름을 읽기 어려워요. ${insight.minRecords}건 이상 모이면 변화를 정리해 드릴게요.`
        : `최근 ${insight.days}일간 확인 가능한 기록이 ${insight.recordCount}건으로, 변화 흐름을 해석하기에 부족합니다(기준 ${insight.minRecords}건).`,
    );
    return lines;
  }
  const { prevAvg, recentAvg, diff, direction } = insight.change;
  if (direction === "unknown") {
    lines.push(
      s
        ? "기록이 한쪽 기간에 몰려 있어서 이전과 최근을 비교하기는 아직 어려워요."
        : "기록이 한쪽 기간에 몰려 있어 이전·최근 기간 비교는 어렵습니다.",
    );
  } else if (direction === "steady") {
    lines.push(
      s
        ? `최근 7일 평균 마음 점수는 ${recentAvg}점으로, 그 전 7일(${prevAvg}점)과 비슷하게 유지되고 있어요.`
        : `최근 7일 평균 ${recentAvg}점, 이전 7일 평균 ${prevAvg}점으로 큰 변화는 보이지 않습니다.`,
    );
  } else {
    const word = direction === "down" ? "낮아" : "높아";
    lines.push(
      s
        ? `최근 7일 평균 마음 점수는 ${recentAvg}점으로, 그 전 7일(${prevAvg}점)보다 ${Math.abs(diff!)}점 ${word}졌어요.`
        : `최근 7일 평균 ${recentAvg}점으로 이전 7일(${prevAvg}점) 대비 ${Math.abs(diff!)}점 ${word}졌습니다.`,
    );
  }
  const top = insight.topics[0];
  if (top) {
    lines.push(
      s
        ? `마음이 무거웠던 날의 기록에서 '${top.label}'와 관련된 표현이 ${top.count}번 나왔어요.`
        : `공유된 기록 중 '${top.label}' 관련 표현이 ${top.count}건 반복됩니다.`,
    );
  }
  const shift = insight.changePoints.find((c) => c.kind === "shift");
  if (shift) {
    lines.push(
      s
        ? `${dayLabel(shift.date)}부터 흐름이 달라지기 시작한 것으로 보여요.`
        : `${dayLabel(shift.date)}부터 변화가 나타나기 시작한 것으로 보입니다.`,
    );
  }
  const main = insight.ratio[0];
  if (main && direction !== "down") {
    lines.push(
      s
        ? `가장 자주 고른 감정은 ${EMOTIONS[main.emotion].emoji} '${EMOTIONS[main.emotion].label}'(${main.pct}%)예요.`
        : `가장 많이 기록된 감정은 '${EMOTIONS[main.emotion].label}'(${main.pct}%)입니다.`,
    );
  }
  return lines;
}
