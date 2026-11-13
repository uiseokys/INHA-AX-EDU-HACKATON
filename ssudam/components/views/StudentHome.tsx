"use client";

import { ArrowRight, Flame, HeartHandshake, LineChart } from "lucide-react";
import Link from "next/link";
import { MoodChart } from "@/components/charts";
import { CheckinCard } from "@/components/student/CheckinCard";
import { ReflectionCard } from "@/components/student/ReflectionCard";
import { TodoCard } from "@/components/student/TodoCard";
import { btn, Card, CardTitle, Chip, cn, PageSkeleton } from "@/components/ui";
import { buildSeries } from "@/lib/analysis";
import { getStudent, logsFor, ME_ID, SCHOOL } from "@/lib/data";
import { addDays, fullLabel, weekday } from "@/lib/date";
import { EMOTIONS } from "@/lib/emotions";
import { useApp } from "@/lib/store";

export function StudentHome() {
  const { ready, state, today } = useApp();
  if (!ready) return <PageSkeleton />;

  const me = getStudent(ME_ID)!;
  const logs = logsFor(ME_ID, state, today);
  const byDate = new Map(logs.map((l) => [l.date, l]));
  const series = buildSeries(logs, today, 14);
  const recordedToday = byDate.has(today);

  // 연속 기록 일수 (오늘 기록 전이면 어제까지 이어진 일수)
  let streak = 0;
  for (let d = recordedToday ? today : addDays(today, -1); byDate.has(d); d = addDays(d, -1)) streak++;

  const week = Array.from({ length: 7 }, (_, i) => addDays(today, i - 6));

  return (
    <div className="animate-fade-up space-y-5">
      {/* 인사 + 이번 주 기록 도장 */}
      <section className="overflow-hidden rounded-3xl bg-linear-to-br from-brand-400 via-brand-300 to-peach-300 p-5 text-white shadow-[0_18px_40px_-18px_rgba(109,89,214,0.6)] sm:p-7">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-white/85">
              {fullLabel(today)} · {SCHOOL} {me.grade}학년 {me.classNo}반
            </p>
            <h1 className="mt-1 text-2xl font-extrabold sm:text-3xl">
              {me.name}아, 오늘도 와줘서 반가워 {me.avatar}
            </h1>
            <p className="mt-2 flex flex-wrap items-center gap-2 text-sm text-white/90">
              <span className="inline-flex items-center gap-1 rounded-full bg-white/20 px-3 py-1 font-bold backdrop-blur">
                <Flame className="size-4" /> {streak}일 연속 기록
              </span>
              {recordedToday ? "오늘 체크인까지 마쳤어요!" : "오늘 마음도 살짝 들여다볼까요?"}
            </p>
          </div>
          <ol className="flex gap-1 self-start rounded-3xl bg-white/90 p-1.5 shadow-sm md:self-auto" aria-label="최근 7일 기록">
            {week.map((d) => {
              const log = byDate.get(d);
              return (
                <li
                  key={d}
                  className={cn(
                    "flex w-10 flex-col items-center gap-1 rounded-2xl py-2 text-[11px] font-bold",
                    d === today ? "bg-brand-500 text-white" : "text-ink-soft",
                  )}
                >
                  {weekday(d)}
                  <span className="grid size-7 place-items-center text-lg">
                    {log ? EMOTIONS[log.emotion].emoji : <span className="size-2 rounded-full bg-current opacity-40" />}
                  </span>
                </li>
              );
            })}
          </ol>
        </div>
      </section>

      <div className="grid items-start gap-5 lg:grid-cols-2">
        <TodoCard />
        <CheckinCard />
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardTitle
            icon={<LineChart className="size-5" />}
            title="나의 감정 변화"
            hint="최근 14일 동안의 마음 점수예요."
            action={
              <Link href="/student/insights" className="flex shrink-0 items-center gap-1 text-xs font-bold text-brand-600 hover:underline">
                자세히 <ArrowRight className="size-3.5" />
              </Link>
            }
          />
          {recordedToday && (
            <Chip className="mb-2 animate-pop bg-peach-100 text-peach-500">오늘 기록이 그래프 맨 오른쪽에 반영됐어요</Chip>
          )}
          <MoodChart series={series} today={today} height={230} />
        </Card>
        <div className="lg:col-span-2">
          <ReflectionCard />
        </div>
      </div>

      <section className="flex flex-col gap-4 rounded-3xl border border-white bg-white/85 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <div className="flex items-start gap-3">
          <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-mint-100 text-mint-700">
            <HeartHandshake className="size-6" />
          </span>
          <div>
            <h2 className="text-base font-bold text-ink">이야기하고 싶은 일이 있나요?</h2>
            <p className="mt-0.5 text-sm text-ink-soft">
              감정 기록이 없어도 괜찮아요. 상담 선생님께 조용히 도움을 요청할 수 있어요.
            </p>
          </div>
        </div>
        <Link href="/student/support" className={cn(btn.soft, "shrink-0 bg-mint-100 text-mint-700 hover:bg-mint-200")}>
          상담 지원 요청하기 <ArrowRight className="size-4" />
        </Link>
      </section>
    </div>
  );
}
