"use client";

import {
  ArrowLeft,
  ArrowRight,
  Building2,
  ClipboardCheck,
  EyeOff,
  History,
  LineChart,
  MessageCircleHeart,
  MessageSquareText,
  NotebookPen,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { MoodChart } from "@/components/charts";
import { ChangePointList, RecordRow, TopicList } from "@/components/insight";
import { btn, Card, CardTitle, Chip, cn, field, Notice, PageSkeleton } from "@/components/ui";
import { analyze, summarize } from "@/lib/analysis";
import { agencyTypeLabel, consentFor, getAgency, getStudent, logsFor, referralsFor, requestsFor, statusFor } from "@/lib/data";
import { dayLabel } from "@/lib/date";
import { teacherView } from "@/lib/privacy";
import { STATUS, STATUS_ORDER } from "@/lib/status";
import { useApp } from "@/lib/store";
import type { CaseStatus } from "@/lib/types";

export function TeacherStudent({ id }: { id: string }) {
  const { ready, state, today, update } = useApp();
  if (!ready) return <PageSkeleton />;

  const student = getStudent(id);
  if (!student) {
    return (
      <Card className="text-center">
        <p className="text-sm text-ink-soft">학생 정보를 찾을 수 없습니다.</p>
        <Link href="/teacher" className={cn(btn.soft, "mt-4")}>
          요청 현황으로 돌아가기
        </Link>
      </Card>
    );
  }

  const status = statusFor(student, state);
  const consent = consentFor(student, state);
  // 교사 화면은 공유 동의 범위를 거친 기록만 사용합니다.
  const view = teacherView(logsFor(id, state, today), consent);
  const insight = analyze(view.logs, today);
  const requests = requestsFor(id, state, today);
  const referrals = referralsFor(id, state, today);
  const records = [...view.logs].sort((a, b) => b.date.localeCompare(a.date));

  const timeline = [
    ...requests.map((r) => ({ date: r.date, text: `학생이 상담 지원을 요청함 (${r.topic})` })),
    ...referrals.map((r) => ({ date: r.date, text: `${getAgency(r.agencyId)?.name ?? "지원기관"} 연결 요청` })),
    ...(state.events[id] ?? []),
  ].sort((a, b) => b.date.localeCompare(a.date));

  const setStatus = (next: CaseStatus) => {
    if (next === status) return;
    update((s) => ({
      ...s,
      caseStatus: { ...s.caseStatus, [id]: next },
      events: { ...s.events, [id]: [...(s.events[id] ?? []), { date: today, text: `진행 상태를 ‘${STATUS[next].label}’(으)로 변경` }] },
    }));
  };

  return (
    <div className="animate-fade-up space-y-5">
      <Link href="/teacher" className="inline-flex items-center gap-1 text-sm font-semibold text-ink-soft hover:text-brand-700">
        <ArrowLeft className="size-4" /> 요청 현황
      </Link>

      <Card className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <span className="grid size-16 shrink-0 place-items-center rounded-3xl bg-cream text-4xl">{student.avatar}</span>
          <div>
            <h1 className="flex flex-wrap items-center gap-2 text-2xl font-extrabold text-ink">
              {student.name}
              <Chip className={STATUS[status].chip}>{STATUS[status].label}</Chip>
            </h1>
            <p className="mt-0.5 text-sm text-ink-soft">
              {student.grade}학년 {student.classNo}반 · 가상 학생({student.id})
            </p>
            {student.statusNote && <p className="mt-1 text-sm text-ink">{student.statusNote}</p>}
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5 sm:max-w-56 sm:justify-end">
          <Chip className={consent.trend ? "bg-mint-100 text-mint-700" : "bg-stone-100 text-stone-500"}>
            <ShieldCheck className="size-3" /> 그래프 {consent.trend ? "공유" : "비공유"}
          </Chip>
          <Chip className={view.sharedNoteCount > 0 ? "bg-mint-100 text-mint-700" : "bg-stone-100 text-stone-500"}>
            <ShieldCheck className="size-3" /> 메모 {view.sharedNoteCount}건 공유
          </Chip>
        </div>
      </Card>

      <div className="grid items-start gap-5 lg:grid-cols-5">
        <div className="space-y-5 lg:col-span-3">
          <Card>
            <CardTitle icon={<MessageSquareText className="size-5" />} title="상담 요청 내용" hint="학생이 직접 작성해 보낸 내용입니다." />
            {requests.length > 0 ? (
              <ul className="space-y-2">
                {requests.map((r) => (
                  <li key={r.id} className="rounded-2xl bg-brand-50/70 px-4 py-3.5">
                    <p className="flex flex-wrap items-center gap-x-2 text-xs font-semibold text-brand-700">
                      <span>{r.topic}</span>
                      <span className="font-normal text-ink-soft">{dayLabel(r.date)} · 선호 방식: {r.preferred}</span>
                    </p>
                    <p className="mt-1.5 text-sm leading-relaxed text-ink">{r.message || "메시지 없이 요청했습니다."}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded-2xl bg-stone-50 px-4 py-5 text-sm text-ink-soft">학생이 보낸 상담 요청이 없습니다.</p>
            )}
          </Card>

          <Card>
            <CardTitle
              icon={<LineChart className="size-5" />}
              title="감정 변화 그래프"
              hint={view.trendVisible ? "최근 14일 · 학생이 그래프 공유에 동의했습니다." : undefined}
            />
            {view.trendVisible ? (
              <>
                <MoodChart series={insight.series} today={today} height={240} />
                <div className="mt-4 rounded-2xl bg-stone-50 p-4">
                  <p className="mb-2 flex items-center gap-1.5 text-xs font-bold text-ink-soft">
                    <Sparkles className="size-3.5 text-brand-500" /> 규칙 기반 요약 (참고용)
                  </p>
                  <ul className="space-y-1.5">
                    {summarize(insight, "teacher").map((line) => (
                      <li key={line} className="flex gap-2 text-sm leading-relaxed text-ink">
                        <span className="mt-2 size-1.5 shrink-0 rounded-full bg-brand-400" />
                        {line}
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            ) : (
              <div className="rounded-2xl bg-stone-50 px-4 py-8 text-center">
                <EyeOff className="mx-auto size-6 text-stone-400" />
                <p className="mt-2 text-sm font-semibold text-ink">학생이 감정 변화 그래프를 공유하지 않았습니다</p>
                <p className="mt-1 text-xs text-ink-soft">면담에서 학생이 원할 때 공유를 안내해 주세요. 공유하지 않은 기록은 이 화면에 표시되지 않습니다.</p>
              </div>
            )}
          </Card>

          {view.trendVisible && insight.changePoints.length > 0 && (
            <Card>
              <CardTitle title="변화가 나타난 날" hint="근거가 된 날짜와 기록입니다. 공유하지 않은 메모는 표시되지 않습니다." />
              <ChangePointList points={insight.changePoints} emptyText="" />
            </Card>
          )}

          <Card>
            <CardTitle icon={<MessageCircleHeart className="size-5" />} title="반복적으로 나타나는 고민 주제" hint="학생이 공유한 메모에서만 찾습니다. 눌러서 근거 기록을 확인하세요." />
            <TopicList topics={insight.topics} emptyText="공유된 메모에서 반복되는 주제를 찾지 못했습니다." />
          </Card>

          <Card>
            <CardTitle icon={<NotebookPen className="size-5" />} title="학생이 공유한 기록" hint={`공유 동의 범위 안의 기록 ${records.length}건`} />
            {records.length > 0 ? (
              <ul className="space-y-2">
                {records.map((log) => (
                  <RecordRow key={log.id} log={log} hiddenNoteText="메모는 공유되지 않았습니다" />
                ))}
              </ul>
            ) : (
              <p className="rounded-2xl bg-stone-50 px-4 py-5 text-sm text-ink-soft">학생이 공유한 기록이 없습니다.</p>
            )}
          </Card>
        </div>

        <div className="space-y-5 lg:col-span-2">
          <Card>
            <CardTitle icon={<ClipboardCheck className="size-5" />} title="상담 진행 상태" hint="지원 절차의 현재 단계를 선택하세요." />
            <div className="space-y-1.5" role="radiogroup" aria-label="상담 진행 상태">
              {STATUS_ORDER.map((s) => (
                <button
                  key={s}
                  type="button"
                  role="radio"
                  aria-checked={status === s}
                  onClick={() => setStatus(s)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-2xl border-2 px-3.5 py-2.5 text-left transition",
                    status === s ? "border-brand-300 bg-brand-50" : "border-transparent hover:bg-stone-50",
                  )}
                >
                  <span className={cn("size-2.5 shrink-0 rounded-full", STATUS[s].dot)} />
                  <span>
                    <span className="block text-sm font-semibold text-ink">{STATUS[s].label}</span>
                    <span className="block text-xs text-ink-soft">{STATUS[s].desc}</span>
                  </span>
                </button>
              ))}
            </div>
          </Card>

          <Card>
            <CardTitle icon={<Building2 className="size-5" />} title="지원기관 연결" />
            {referrals.length > 0 ? (
              <ul className="mb-3 space-y-2">
                {referrals.map((r) => {
                  const a = getAgency(r.agencyId);
                  return (
                    <li key={r.id} className="rounded-2xl bg-mint-50 px-4 py-3 text-sm">
                      <p className="font-semibold text-ink">{a?.name}</p>
                      <p className="text-xs text-ink-soft">
                        {a && agencyTypeLabel(a.type)} · {dayLabel(r.date)} 연결 요청(시연)
                      </p>
                      {r.note && <p className="mt-1 text-ink-soft">{r.note}</p>}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="mb-3 text-sm text-ink-soft">아직 연결한 기관이 없습니다.</p>
            )}
            <Link href={`/teacher/agencies?student=${student.id}`} className={cn(btn.primary, "w-full")}>
              지원기관 찾아보기 <ArrowRight className="size-4" />
            </Link>
          </Card>

          <Card>
            <CardTitle icon={<NotebookPen className="size-5" />} title="상담 메모" hint="입력하는 대로 이 브라우저에 저장됩니다." />
            <textarea
              value={state.memos[id] ?? ""}
              onChange={(e) => update((s) => ({ ...s, memos: { ...s.memos, [id]: e.target.value } }))}
              rows={4}
              placeholder="면담 일정, 확인한 내용 등을 적어 두세요."
              aria-label="상담 메모"
              className={field}
            />
          </Card>

          <Card>
            <CardTitle icon={<History className="size-5" />} title="진행 기록" />
            {timeline.length > 0 ? (
              <ol className="space-y-3 border-l-2 border-stone-100 pl-4">
                {timeline.map((e, i) => (
                  <li key={`${e.date}-${i}`} className="relative text-sm">
                    <span className="absolute top-1.5 -left-[21px] size-2 rounded-full bg-brand-300" />
                    <span className="block text-xs text-ink-soft">{dayLabel(e.date)}</span>
                    <span className="text-ink">{e.text}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-ink-soft">아직 진행 기록이 없습니다.</p>
            )}
          </Card>
        </div>
      </div>

      <Notice>
        이 화면의 요약과 주제 분류는 규칙 기반 참고 정보이며 진단·판정이 아닙니다. 표시된 학생과 기록은 모두 시연용 합성
        데이터입니다.
      </Notice>
    </div>
  );
}
