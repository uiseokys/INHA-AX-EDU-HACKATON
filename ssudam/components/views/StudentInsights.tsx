"use client";

import { ArrowRight, CalendarSearch, HeartHandshake, LineChart, Lock, MessageCircleHeart, PieChart, Share2, Sparkles } from "lucide-react";
import Link from "next/link";
import { EmotionDonut, MoodChart } from "@/components/charts";
import { ChangePointList, RecordRow, TopicList } from "@/components/insight";
import { btn, Card, CardTitle, Chip, cn, Notice, PageSkeleton } from "@/components/ui";
import { analyze, summarize } from "@/lib/analysis";
import { logsFor, ME_ID } from "@/lib/data";
import { useApp } from "@/lib/store";

export function StudentInsights() {
  const { ready, state, today, update } = useApp();
  if (!ready) return <PageSkeleton />;

  const logs = logsFor(ME_ID, state, today);
  const insight = analyze(logs, today);
  const summary = summarize(insight, "student");
  const { prevAvg, recentAvg, diff, direction } = insight.change;
  const recent = [...logs].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 6);

  const toggleShare = (id: string, shared: boolean) =>
    update((s) => ({ ...s, shareOverrides: { ...s.shareOverrides, [id]: shared } }));

  return (
    <div className="animate-fade-up space-y-5">
      <header>
        <h1 className="text-2xl font-extrabold text-ink">마음 분석</h1>
        <p className="mt-1 text-sm text-ink-soft">최근 14일 동안 내가 남긴 기록 {insight.recordCount}건을 정리했어요.</p>
      </header>

      <Notice>
        이 화면은 내 기록을 규칙에 따라 정리한 <strong>참고 정보</strong>예요. 학교폭력 피해 여부나 마음 건강 상태를
        진단하지 않아요. 결과가 내 느낌과 다르다면 내 느낌이 더 정확해요.
      </Notice>

      {!insight.enough && (
        <Card className="text-center">
          <p className="text-4xl">🌱</p>
          <h2 className="mt-2 text-lg font-bold text-ink">아직 기록이 조금 부족해요</h2>
          <p className="mx-auto mt-1 max-w-md text-sm text-ink-soft">
            지금까지 {insight.recordCount}건을 남겼어요. {insight.minRecords}건 이상 모이면 변화 흐름과 고민 주제를
            정리해 드릴게요. 하루 10초면 충분해요.
          </p>
          <Link href="/student" className={cn(btn.primary, "mt-4")}>
            오늘 마음 기록하러 가기
          </Link>
        </Card>
      )}

      <Card className="bg-linear-to-br from-brand-50 to-white">
        <CardTitle
          icon={<Sparkles className="size-5" />}
          title="쓰담 AI가 정리한 최근 2주"
          action={<Chip className="bg-white text-ink-soft ring-1 ring-stone-200">규칙 기반 분석 · 시연용</Chip>}
        />
        <ul className="space-y-2">
          {summary.map((line) => (
            <li key={line} className="flex gap-2.5 text-sm leading-relaxed text-ink">
              <span className="mt-2 size-1.5 shrink-0 rounded-full bg-brand-400" />
              {line}
            </li>
          ))}
        </ul>
        {insight.enough && direction !== "unknown" && (
          <dl className="mt-5 grid grid-cols-3 gap-2 text-center sm:gap-3">
            <div className="rounded-2xl bg-white p-3 ring-1 ring-stone-100">
              <dt className="text-[11px] font-semibold text-ink-soft">이전 7일 평균</dt>
              <dd className="mt-1 text-xl font-extrabold text-ink">{prevAvg}</dd>
            </div>
            <div className="rounded-2xl bg-white p-3 ring-1 ring-stone-100">
              <dt className="text-[11px] font-semibold text-ink-soft">최근 7일 평균</dt>
              <dd className="mt-1 text-xl font-extrabold text-ink">{recentAvg}</dd>
            </div>
            <div className="rounded-2xl bg-white p-3 ring-1 ring-stone-100">
              <dt className="text-[11px] font-semibold text-ink-soft">변화</dt>
              <dd className={cn("mt-1 text-xl font-extrabold", direction === "down" ? "text-peach-500" : direction === "up" ? "text-mint-500" : "text-ink")}>
                {diff! > 0 ? "+" : ""}
                {diff}
              </dd>
            </div>
          </dl>
        )}
      </Card>

      {direction === "down" && (
        <section className="flex flex-col gap-3 rounded-3xl bg-mint-50 p-5 ring-1 ring-mint-100 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-start gap-3 text-sm leading-relaxed text-ink">
            <HeartHandshake className="mt-0.5 size-5 shrink-0 text-mint-500" />
            <span>
              요즘 마음이 무거운 날이 이어졌네요. 혼자 감당하기 버거울 땐 상담 선생님과 이야기해 볼 수 있어요.
              요청할지는 내가 정해요.
            </span>
          </p>
          <Link href="/student/support" className={cn(btn.soft, "shrink-0 bg-white text-mint-700 hover:bg-mint-100")}>
            도움 요청 살펴보기 <ArrowRight className="size-4" />
          </Link>
        </section>
      )}

      <div className="grid items-start gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardTitle icon={<LineChart className="size-5" />} title="최근 14일 감정 변화" hint="점 위에 마우스를 올리거나 눌러 보면 그날의 기록이 보여요." />
          <MoodChart series={insight.series} today={today} height={260} />
        </Card>
        <Card className="lg:col-span-2">
          <CardTitle icon={<PieChart className="size-5" />} title="감정별 기록 비율" />
          {insight.ratio.length > 0 ? (
            <EmotionDonut ratio={insight.ratio} />
          ) : (
            <p className="rounded-2xl bg-stone-50 px-4 py-5 text-sm text-ink-soft">아직 기록이 없어요.</p>
          )}
        </Card>
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-2">
        <Card>
          <CardTitle
            icon={<MessageCircleHeart className="size-5" />}
            title="자주 언급한 고민 주제"
            hint="마음이 무거웠던 날의 메모에서 찾았어요. 눌러서 근거를 확인해요."
          />
          <TopicList topics={insight.topics} emptyText="메모에서 반복되는 고민 주제를 찾지 못했어요. 메모를 남기면 여기에 정리돼요." />
        </Card>
        <Card>
          <CardTitle icon={<CalendarSearch className="size-5" />} title="변화가 나타난 날" hint="흐름이 달라지기 시작한 날과 그날의 기록이에요." />
          <ChangePointList points={insight.changePoints} emptyText="최근 2주 동안 눈에 띄게 달라진 날은 없었어요." />
        </Card>
      </div>

      <Card>
        <CardTitle title="최근 기록" hint="기록마다 상담 선생님과 공유할지 내가 정할 수 있어요." />
        <ul className="space-y-2">
          {recent.map((log) => (
            <RecordRow
              key={log.id}
              log={log}
              right={
                <button
                  type="button"
                  onClick={() => toggleShare(log.id, !log.shared)}
                  aria-pressed={log.shared}
                  className={cn(
                    "flex shrink-0 items-center gap-1 rounded-full px-3 py-1.5 text-xs font-semibold transition",
                    log.shared ? "bg-mint-100 text-mint-700 hover:bg-mint-200" : "bg-stone-100 text-ink-soft hover:bg-stone-200",
                  )}
                >
                  {log.shared ? <Share2 className="size-3" /> : <Lock className="size-3" />}
                  {log.shared ? "공유 중" : "나만 보기"}
                </button>
              }
            />
          ))}
          {recent.length === 0 && <li className="rounded-2xl bg-stone-50 px-4 py-5 text-sm text-ink-soft">아직 기록이 없어요.</li>}
        </ul>
      </Card>
    </div>
  );
}
