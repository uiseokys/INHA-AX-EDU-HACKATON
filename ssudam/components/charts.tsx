"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Insight, SeriesPoint } from "@/lib/analysis";
import { dayLabel } from "@/lib/date";
import { EMOTIONS, INTENSITY_LABELS } from "@/lib/emotions";

function MoodTip({ active, payload }: { active?: boolean; payload?: readonly { payload?: SeriesPoint }[] }) {
  const p = payload?.[0]?.payload;
  if (!active || !p) return null;
  return (
    <div className="max-w-56 rounded-2xl border border-stone-100 bg-white px-3.5 py-3 text-xs shadow-lg">
      <p className="font-bold text-ink">{dayLabel(p.date)}</p>
      {p.score === null || !p.emotion ? (
        <p className="mt-1 text-ink-soft">기록 없음</p>
      ) : (
        <>
          <p className="mt-1 text-sm">
            {EMOTIONS[p.emotion].emoji} {EMOTIONS[p.emotion].label}
            <span className="text-ink-soft"> · {INTENSITY_LABELS[p.intensity ?? 3]}</span>
          </p>
          <p className="mt-1 text-ink-soft">
            마음 점수 <strong className="text-brand-600">{p.score}</strong>
            {p.avg !== null && <> · 이동평균 {p.avg}</>}
          </p>
          {p.note && <p className="mt-1.5 border-t border-stone-100 pt-1.5 text-ink-soft">“{p.note}”</p>}
        </>
      )}
    </div>
  );
}

interface DotProps {
  cx?: number;
  cy?: number;
  index?: number;
  payload?: SeriesPoint;
}

/** 최근 14일 마음 점수 그래프 (실선: 그날의 점수, 점선: 최근 3회 이동평균) */
export function MoodChart({
  series,
  today,
  height = 240,
}: {
  series: SeriesPoint[];
  today: string;
  height?: number;
}) {
  const renderDot = ({ cx, cy, index, payload }: DotProps) => {
    if (cx == null || cy == null || !payload || payload.score === null) return <g key={index} />;
    const isToday = payload.date === today;
    return (
      <g key={index}>
        {isToday && <circle cx={cx} cy={cy} r={9} fill="#ffb98f" opacity={0.45} />}
        <circle cx={cx} cy={cy} r={isToday ? 5 : 3.5} fill="#fff" stroke={isToday ? "#e9834f" : "#8572ec"} strokeWidth={2.5} />
      </g>
    );
  };

  return (
    <div>
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={series} margin={{ top: 14, right: 14, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="moodFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#9f8ef5" stopOpacity={0.28} />
                <stop offset="1" stopColor="#9f8ef5" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#efeaf7" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: "#9a95ae" }}
              tickLine={false}
              axisLine={false}
              ticks={series.filter((_, i) => (series.length - 1 - i) % 2 === 0).map((p) => p.label)}
              interval={0}
            />
            <YAxis
              domain={[1, 5]}
              ticks={[1, 2, 3, 4, 5]}
              width={30}
              tick={{ fontSize: 11, fill: "#9a95ae" }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<MoodTip />} cursor={{ stroke: "#d8cfff", strokeDasharray: "4 4" }} />
            <Area type="monotone" dataKey="score" stroke="none" fill="url(#moodFill)" connectNulls tooltipType="none" />
            <Line
              type="monotone"
              dataKey="avg"
              stroke="#f99f6d"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              activeDot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="score"
              stroke="#8572ec"
              strokeWidth={2.5}
              connectNulls
              dot={renderDot}
              activeDot={{ r: 6, fill: "#8572ec", stroke: "#fff", strokeWidth: 2 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-ink-soft">
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded bg-brand-500" /> 그날의 마음 점수
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-4 border-t-2 border-dashed border-peach-400" /> 최근 3회 평균
        </span>
        <span>5 가벼움 · 3 보통 · 1 무거움</span>
      </div>
    </div>
  );
}

/** 감정별 기록 비율 도넛 + 범례 */
export function EmotionDonut({ ratio }: { ratio: Insight["ratio"] }) {
  const data = ratio.map((r) => ({
    name: EMOTIONS[r.emotion].label,
    count: r.count,
    fill: EMOTIONS[r.emotion].color,
  }));
  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row">
      <div className="size-40 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="name"
              innerRadius={46}
              outerRadius={74}
              paddingAngle={3}
              cornerRadius={6}
              stroke="none"
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="w-full space-y-2">
        {ratio.map((r) => (
          <li key={r.emotion} className="flex items-center gap-2 text-sm">
            <span className="w-6 text-center text-lg">{EMOTIONS[r.emotion].emoji}</span>
            <span className="w-20 shrink-0 text-ink">{EMOTIONS[r.emotion].label}</span>
            <span className="h-2 flex-1 overflow-hidden rounded-full bg-stone-100">
              <span
                className="block h-full rounded-full transition-all duration-500"
                style={{ width: `${r.pct}%`, background: EMOTIONS[r.emotion].color }}
              />
            </span>
            <span className="w-16 shrink-0 text-right text-xs text-ink-soft">
              {r.count}회 · {r.pct}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** 목록용 작은 추이선 */
export function Sparkline({ series }: { series: SeriesPoint[] }) {
  const w = 96;
  const h = 32;
  const pts = series
    .map((p, i) => (p.score === null ? null : { x: (i / (series.length - 1)) * (w - 6) + 3, y: h - 4 - ((p.score - 1) / 4) * (h - 8) }))
    .filter((p): p is { x: number; y: number } => p !== null);
  if (pts.length < 2) return <span className="text-xs text-stone-400">기록 적음</span>;
  const last = pts[pts.length - 1];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-8 w-24" role="img" aria-label="최근 14일 마음 점수 추이">
      <polyline
        points={pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ")}
        fill="none"
        stroke="#9f8ef5"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={last.x} cy={last.y} r="3" fill="#fff" stroke="#8572ec" strokeWidth="2" />
    </svg>
  );
}
