"use client";

import { ChevronRight, EyeOff, MessageSquareText, TrendingDown } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Sparkline } from "@/components/charts";
import { Chip, cn, Notice, PageSkeleton } from "@/components/ui";
import { analyze } from "@/lib/analysis";
import { consentFor, logsFor, requestsFor, SCHOOL, statusFor, students } from "@/lib/data";
import { relativeLabel } from "@/lib/date";
import { teacherView } from "@/lib/privacy";
import { STATUS, STATUS_ORDER } from "@/lib/status";
import { useApp } from "@/lib/store";
import type { CaseStatus } from "@/lib/types";

const TILES: CaseStatus[] = ["requested", "review", "in_progress", "referred"];

export function TeacherHome() {
  const { ready, state, today } = useApp();
  const [filter, setFilter] = useState<CaseStatus | "all">("all");
  if (!ready) return <PageSkeleton />;

  const rows = students
    .map((student) => {
      const status = statusFor(student, state);
      // 교사 화면은 공유 동의 범위를 거친 기록만 사용합니다.
      const view = teacherView(logsFor(student.id, state, today), consentFor(student, state));
      const insight = analyze(view.logs, today);
      const request = requestsFor(student.id, state, today)[0];
      return { student, status, view, insight, request };
    })
    .sort(
      (a, b) =>
        STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status) ||
        (b.request?.date ?? "").localeCompare(a.request?.date ?? ""),
    );

  const count = (s: CaseStatus) => rows.filter((r) => r.status === s).length;
  const visible = filter === "all" ? rows : rows.filter((r) => r.status === filter);

  return (
    <div className="animate-fade-up space-y-5">
      <header className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-ink">상담 지원 현황</h1>
          <p className="mt-1 text-sm text-ink-soft">{SCHOOL} · 학생이 공유에 동의한 정보만 표시됩니다.</p>
        </div>
        <Chip className="self-start bg-white text-ink-soft ring-1 ring-stone-200 sm:self-auto">합성 데이터 · 가상 학생 {students.length}명</Chip>
      </header>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {TILES.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setFilter(filter === s ? "all" : s)}
            aria-pressed={filter === s}
            className={cn(
              "rounded-3xl border-2 p-4 text-left transition hover:-translate-y-0.5",
              STATUS[s].tile,
              filter === s ? "border-current shadow-md" : "border-transparent",
            )}
          >
            <span className="flex items-center gap-2 text-xs font-bold">
              <span className={cn("size-2 rounded-full", STATUS[s].dot)} />
              {STATUS[s].label}
            </span>
            <span className="mt-1 block text-3xl font-extrabold">{count(s)}</span>
            <span className="mt-0.5 block text-[11px] opacity-80">{STATUS[s].desc}</span>
          </button>
        ))}
      </div>

      <section className="rounded-3xl border border-white/80 bg-white/90 p-3 shadow-[0_10px_30px_-12px_rgba(56,164,138,0.2)] sm:p-5">
        <div className="mb-3 flex flex-wrap items-center gap-1.5 px-1">
          {(["all", ...STATUS_ORDER] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setFilter(s)}
              aria-pressed={filter === s}
              className={cn(
                "rounded-full px-3 py-1.5 text-xs font-semibold transition",
                filter === s ? "bg-ink text-white" : "bg-stone-100 text-ink-soft hover:bg-stone-200",
              )}
            >
              {s === "all" ? `전체 ${rows.length}` : `${STATUS[s].label} ${count(s)}`}
            </button>
          ))}
        </div>

        <div className="hidden grid-cols-[1.3fr_1fr_2fr_1.3fr_7rem_1.5rem] gap-4 px-4 pb-2 text-[11px] font-bold text-stone-400 lg:grid">
          <span>학생</span>
          <span>진행 상태</span>
          <span>최근 요청 · 메모</span>
          <span>공유 범위 · 참고 정보</span>
          <span>14일 추이</span>
          <span />
        </div>

        <ul className="space-y-2">
          {visible.map(({ student, status, view, insight, request }) => {
            const isNew = status === "requested" && request?.date === today;
            const topic = insight.topics[0];
            const changed = view.trendVisible && insight.enough && insight.change.direction === "down";
            return (
              <li key={student.id}>
                <Link
                  href={`/teacher/students/${student.id}`}
                  className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-3 rounded-2xl border border-stone-100 bg-white px-4 py-3.5 transition hover:border-brand-200 hover:shadow-md lg:grid-cols-[1.3fr_1fr_2fr_1.3fr_7rem_1.5rem]"
                >
                  <span className="flex items-center gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-cream text-xl">{student.avatar}</span>
                    <span>
                      <span className="flex items-center gap-1.5 text-sm font-bold text-ink">
                        {student.name}
                        {isNew && (
                          <span className="relative flex size-2">
                            <span className="absolute inline-flex size-full animate-ping rounded-full bg-brand-400 opacity-60" />
                            <span className="relative inline-flex size-2 rounded-full bg-brand-500" />
                          </span>
                        )}
                      </span>
                      <span className="block text-xs text-ink-soft">
                        {student.grade}학년 {student.classNo}반
                      </span>
                    </span>
                  </span>

                  <span className="justify-self-end lg:justify-self-start">
                    <Chip className={STATUS[status].chip}>{STATUS[status].label}</Chip>
                  </span>

                  <span className="col-span-2 min-w-0 text-sm lg:col-span-1">
                    {request ? (
                      <>
                        <span className="flex items-center gap-1.5 text-xs font-semibold text-ink">
                          <MessageSquareText className="size-3.5 text-brand-500" />
                          {request.topic} · {relativeLabel(request.date, today)}
                          {isNew && <span className="text-brand-600">새 요청</span>}
                        </span>
                        <span className="mt-0.5 block truncate text-ink-soft">{request.message || "메시지 없이 요청"}</span>
                      </>
                    ) : (
                      <span className="text-ink-soft">{student.statusNote || "요청 없음"}</span>
                    )}
                  </span>

                  <span className="col-span-2 flex flex-wrap gap-1.5 lg:col-span-1">
                    {view.logs.length === 0 ? (
                      <Chip className="bg-stone-100 text-stone-500">
                        <EyeOff className="size-3" /> 공유한 기록 없음
                      </Chip>
                    ) : (
                      <>
                        {view.trendVisible && <Chip className="bg-brand-50 text-brand-700">그래프</Chip>}
                        <Chip className="bg-brand-50 text-brand-700">메모 {view.sharedNoteCount}건</Chip>
                      </>
                    )}
                    {changed && (
                      <Chip className="bg-butter-100 text-amber-800">
                        <TrendingDown className="size-3" /> 평균 {insight.change.diff}
                      </Chip>
                    )}
                    {topic && <Chip className="bg-stone-100 text-ink-soft">{topic.emoji} {topic.label}</Chip>}
                  </span>

                  <span className="hidden lg:block">
                    {view.trendVisible ? <Sparkline series={insight.series} /> : <span className="text-xs text-stone-400">그래프 비공유</span>}
                  </span>
                  <ChevronRight className="hidden size-5 text-stone-300 lg:block" />
                </Link>
              </li>
            );
          })}
          {visible.length === 0 && (
            <li className="rounded-2xl bg-stone-50 px-4 py-8 text-center text-sm text-ink-soft">이 상태에 해당하는 학생이 없습니다.</li>
          )}
        </ul>
      </section>

      <Notice>
        ‘변화 검토 필요’와 ‘평균 ↓’ 표시는 공유된 기록을 규칙으로 계산한 <strong>참고 신호</strong>이며, 학교폭력 피해나
        위험 여부에 대한 판정이 아닙니다. 지원 여부는 학생과의 면담을 통해 상담교사가 판단합니다.
      </Notice>
    </div>
  );
}
