"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";
import type { ChangePoint, TopicResult } from "@/lib/analysis";
import { dayLabel } from "@/lib/date";
import { EMOTIONS, INTENSITY_LABELS } from "@/lib/emotions";
import type { EmotionLog } from "@/lib/types";
import { cn } from "./ui";

/** 메모에서 근거가 된 키워드를 강조 */
function Highlight({ text, words }: { text: string; words: string[] }) {
  if (words.length === 0) return <>{text}</>;
  const sorted = [...words].sort((a, b) => b.length - a.length);
  const parts: { t: string; hit: boolean }[] = [];
  let rest = text;
  while (rest.length > 0) {
    let best: { idx: number; w: string } | null = null;
    for (const w of sorted) {
      const idx = rest.indexOf(w);
      if (idx >= 0 && (best === null || idx < best.idx)) best = { idx, w };
    }
    if (!best) {
      parts.push({ t: rest, hit: false });
      break;
    }
    if (best.idx > 0) parts.push({ t: rest.slice(0, best.idx), hit: false });
    parts.push({ t: best.w, hit: true });
    rest = rest.slice(best.idx + best.w.length);
  }
  return (
    <>
      {parts.map((p, i) =>
        p.hit ? (
          <mark key={i} className="rounded bg-butter-200 px-0.5 text-ink">
            {p.t}
          </mark>
        ) : (
          <span key={i}>{p.t}</span>
        ),
      )}
    </>
  );
}

/** 고민 주제 목록. 각 주제를 누르면 근거가 된 기록이 펼쳐집니다. */
export function TopicList({ topics, emptyText }: { topics: TopicResult[]; emptyText: string }) {
  const [open, setOpen] = useState<string | null>(topics[0]?.id ?? null);
  if (topics.length === 0) return <p className="rounded-2xl bg-stone-50 px-4 py-5 text-sm text-ink-soft">{emptyText}</p>;
  const max = topics[0].count;
  return (
    <ul className="space-y-2">
      {topics.map((t) => {
        const isOpen = open === t.id;
        return (
          <li key={t.id} className="overflow-hidden rounded-2xl border border-stone-100 bg-white">
            <button
              type="button"
              onClick={() => setOpen(isOpen ? null : t.id)}
              aria-expanded={isOpen}
              className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-brand-50/50"
            >
              <span className="text-xl">{t.emoji}</span>
              <span className="w-24 shrink-0 text-sm font-semibold text-ink">{t.label}</span>
              <span className="h-2 flex-1 overflow-hidden rounded-full bg-stone-100">
                <span
                  className="block h-full rounded-full bg-brand-300 transition-all duration-500"
                  style={{ width: `${(t.count / max) * 100}%` }}
                />
              </span>
              <span className="w-8 shrink-0 text-right text-xs font-semibold text-ink-soft">{t.count}회</span>
              <ChevronDown className={cn("size-4 shrink-0 text-stone-400 transition", isOpen && "rotate-180")} />
            </button>
            {isOpen && (
              <div className="animate-fade-up border-t border-stone-100 bg-stone-50/60 px-4 py-3">
                <p className="mb-2 text-[11px] font-semibold text-ink-soft">근거가 된 기록</p>
                <ul className="space-y-1.5">
                  {t.evidence.map((e) => (
                    <li key={e.date} className="flex gap-2 text-sm leading-relaxed">
                      <span className="w-16 shrink-0 text-xs leading-6 text-ink-soft">{dayLabel(e.date)}</span>
                      <span>{EMOTIONS[e.emotion].emoji}</span>
                      <span className="text-ink">
                        <Highlight text={e.note} words={e.matched} />
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/** 변화가 나타난 날짜와 그날의 기록 */
export function ChangePointList({ points, emptyText }: { points: ChangePoint[]; emptyText: string }) {
  if (points.length === 0) return <p className="rounded-2xl bg-stone-50 px-4 py-5 text-sm text-ink-soft">{emptyText}</p>;
  return (
    <ol className="space-y-3">
      {points.map((c) => (
        <li key={`${c.kind}-${c.date}`} className="relative rounded-2xl border border-stone-100 bg-white p-4 pl-5">
          <span className="absolute inset-y-4 left-0 w-1 rounded-r-full bg-peach-300" />
          <p className="text-sm font-bold text-ink">{dayLabel(c.date)}</p>
          <p className="mt-0.5 text-xs text-ink-soft">{c.description}</p>
          <p className="mt-2 rounded-xl bg-stone-50 px-3 py-2 text-sm text-ink">
            {EMOTIONS[c.log.emotion].emoji} {EMOTIONS[c.log.emotion].label}
            <span className="text-ink-soft"> · {INTENSITY_LABELS[c.log.intensity]}</span>
            {c.log.note && <span className="mt-1 block text-ink-soft">“{c.log.note}”</span>}
          </p>
        </li>
      ))}
    </ol>
  );
}

/** 감정 기록 한 줄 */
export function RecordRow({
  log,
  right,
  hiddenNoteText,
}: {
  log: EmotionLog;
  right?: React.ReactNode;
  /** 메모가 없을 때 보여 줄 문구 */
  hiddenNoteText?: string;
}) {
  const e = EMOTIONS[log.emotion];
  return (
    <li className="flex items-start gap-3 rounded-2xl border border-stone-100 bg-white px-4 py-3">
      <span className="text-2xl leading-8">{e.emoji}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-ink">
          {e.label}
          <span className="font-normal text-ink-soft">
            {" "}
            · {INTENSITY_LABELS[log.intensity]} · {dayLabel(log.date)}
          </span>
        </p>
        <p className={cn("mt-0.5 text-sm leading-relaxed", log.note ? "text-ink-soft" : "text-stone-400")}>
          {log.note ?? hiddenNoteText ?? "메모 없이 기록했어요"}
        </p>
      </div>
      {right}
    </li>
  );
}
