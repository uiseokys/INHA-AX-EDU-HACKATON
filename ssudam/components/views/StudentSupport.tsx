"use client";

import { ArrowRight, Check, HeartHandshake, Phone, Send, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { btn, Card, CardTitle, cn, field, Notice, PageSkeleton } from "@/components/ui";
import { getStudent, ME_ID, requestsFor, statusFor } from "@/lib/data";
import { dayLabel } from "@/lib/date";
import { newId, useApp } from "@/lib/store";
import type { CaseStatus } from "@/lib/types";

const TOPICS = ["친구 관계", "학업", "가족", "진로", "몸과 마음", "말하기 어려워요"];
const PREFERRED = ["직접 만나서 이야기하기", "쪽지·메신저로 먼저", "선생님이 먼저 불러주세요"];

const STEPS = ["요청 보냄", "선생님 확인", "상담 진행", "필요하면 기관 연결"];
const STEP_OF: Record<CaseStatus, number> = { none: -1, requested: 0, review: 1, in_progress: 2, referred: 3, closed: 3 };
const STATUS_TEXT: Record<CaseStatus, string> = {
  none: "진행 중인 요청이 없어요.",
  requested: "요청이 전달됐어요. 상담 선생님이 확인하면 알려 드릴게요.",
  review: "상담 선생님이 내용을 살펴보고 있어요.",
  in_progress: "상담 선생님과의 상담이 진행되고 있어요.",
  referred: "선생님이 도움이 될 전문기관과 연결하고 있어요.",
  closed: "지원이 마무리됐어요. 언제든 다시 요청할 수 있어요.",
};

function Toggle({ checked, onChange, title, desc }: { checked: boolean; onChange: (v: boolean) => void; title: string; desc: string }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-3 rounded-2xl bg-stone-50 px-4 py-3">
      <span className="text-sm text-ink">
        <span className="font-semibold">{title}</span>
        <span className="block text-xs text-ink-soft">{desc}</span>
      </span>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="peer sr-only" />
      <span className="relative h-6 w-11 shrink-0 rounded-full bg-stone-300 transition peer-checked:bg-mint-400 peer-focus-visible:ring-4 peer-focus-visible:ring-brand-100 after:absolute after:top-0.5 after:left-0.5 after:size-5 after:rounded-full after:bg-white after:shadow after:transition peer-checked:after:translate-x-5" />
    </label>
  );
}

export function StudentSupport() {
  const { ready, state, today, update } = useApp();
  const [topic, setTopic] = useState("");
  const [message, setMessage] = useState("");
  const [preferred, setPreferred] = useState(PREFERRED[0]);
  const [justSent, setJustSent] = useState(false);

  if (!ready) return <PageSkeleton />;

  const me = getStudent(ME_ID)!;
  const status = statusFor(me, state);
  const requests = requestsFor(ME_ID, state, today);
  const step = STEP_OF[status];

  const setConsent = (patch: Partial<typeof state.consent>) =>
    update((s) => ({ ...s, consent: { ...s.consent, ...patch } }));

  const submit = () => {
    update((s) => ({
      ...s,
      requests: [
        ...s.requests,
        { id: newId("REQ"), studentId: ME_ID, date: today, topic: topic || "주제를 고르지 않음", message: message.trim(), preferred },
      ],
      caseStatus: { ...s.caseStatus, [ME_ID]: "requested" },
    }));
    setTopic("");
    setMessage("");
    setJustSent(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="animate-fade-up space-y-5">
      <header>
        <h1 className="text-2xl font-extrabold text-ink">도움 요청</h1>
        <p className="mt-1 text-sm text-ink-soft">
          감정 기록을 하지 않았어도 괜찮아요. 말하고 싶은 만큼만 적어서 상담 선생님께 보낼 수 있어요.
        </p>
      </header>

      {requests.length > 0 && (
        <Card className={cn(justSent && "animate-pop ring-2 ring-mint-200")}>
          <CardTitle icon={<HeartHandshake className="size-5" />} title={justSent ? "요청을 보냈어요 💌" : "내 요청 진행 상황"} hint={STATUS_TEXT[status]} />
          <ol className="grid grid-cols-4 gap-1.5">
            {STEPS.map((label, i) => (
              <li key={label} className="text-center">
                <span
                  className={cn(
                    "mx-auto grid size-8 place-items-center rounded-full text-xs font-bold transition",
                    i <= step ? "bg-mint-400 text-white" : "bg-stone-100 text-stone-400",
                  )}
                >
                  {i < step ? <Check className="size-4" strokeWidth={3} /> : i + 1}
                </span>
                <span className={cn("mt-1.5 block text-[11px] font-semibold", i <= step ? "text-mint-700" : "text-stone-400")}>{label}</span>
              </li>
            ))}
          </ol>
          <ul className="mt-4 space-y-2">
            {requests.map((r) => (
              <li key={r.id} className="rounded-2xl bg-stone-50 px-4 py-3 text-sm">
                <p className="font-semibold text-ink">
                  {r.topic} <span className="font-normal text-ink-soft">· {dayLabel(r.date)} · {r.preferred}</span>
                </p>
                <p className="mt-0.5 text-ink-soft">{r.message || "메시지 없이 요청했어요."}</p>
              </li>
            ))}
          </ul>
          <Link href="/teacher" className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-brand-600 hover:underline">
            (시연용) 상담교사 화면에서 이 요청 확인하기 <ArrowRight className="size-3.5" />
          </Link>
        </Card>
      )}

      <div className="grid items-start gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardTitle icon={<Send className="size-5" />} title="상담 선생님께 요청 보내기" hint="모든 항목은 선택이에요. 빈칸으로 보내도 돼요." />
          <div className="space-y-5">
            <fieldset>
              <legend className="mb-2 text-sm font-semibold text-ink">어떤 이야기를 하고 싶나요?</legend>
              <div className="flex flex-wrap gap-2">
                {TOPICS.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTopic(topic === t ? "" : t)}
                    aria-pressed={topic === t}
                    className={cn(
                      "rounded-full px-3.5 py-2 text-sm font-semibold transition",
                      topic === t ? "bg-brand-500 text-white shadow-sm" : "bg-stone-100 text-ink-soft hover:bg-brand-50 hover:text-brand-700",
                    )}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </fieldset>

            <div>
              <label htmlFor="support-message" className="mb-2 block text-sm font-semibold text-ink">
                선생님께 전하고 싶은 말
              </label>
              <textarea
                id="support-message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={4}
                maxLength={500}
                placeholder="예: 요즘 반에서 지내는 게 조금 힘들어요. 조용히 이야기하고 싶어요."
                className={field}
              />
            </div>

            <fieldset>
              <legend className="mb-2 text-sm font-semibold text-ink">어떻게 만나면 편할까요?</legend>
              <div className="grid gap-2 sm:grid-cols-3">
                {PREFERRED.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setPreferred(p)}
                    aria-pressed={preferred === p}
                    className={cn(
                      "rounded-2xl border-2 px-3 py-3 text-sm font-semibold transition",
                      preferred === p ? "border-brand-400 bg-brand-50 text-brand-700" : "border-transparent bg-stone-50 text-ink-soft hover:bg-brand-50/60",
                    )}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </fieldset>

            <button type="button" onClick={submit} className={cn(btn.primary, "w-full")}>
              <Send className="size-4" /> 상담 지원 요청 보내기
            </button>
            <p className="text-center text-xs text-ink-soft">시연용 화면이에요. 실제 상담 접수는 이루어지지 않아요.</p>
          </div>
        </Card>

        <div className="space-y-5 lg:col-span-2">
          <Card>
            <CardTitle icon={<ShieldCheck className="size-5" />} title="공유 범위는 내가 정해요" hint="켜 둔 정보만 상담 선생님 화면에 보여요. 언제든 바꿀 수 있어요." />
            <div className="space-y-2">
              <Toggle
                checked={state.consent.trend}
                onChange={(v) => setConsent({ trend: v })}
                title="감정 변화 그래프 공유"
                desc="날짜별 이모지와 강도만 전달돼요."
              />
              <Toggle
                checked={state.consent.allNotes}
                onChange={(v) => setConsent({ allNotes: v })}
                title="내가 쓴 메모도 모두 공유"
                desc="꺼 두면 ‘공유 중’으로 표시한 기록의 메모만 보여요."
              />
            </div>
            <p className="mt-3 text-xs leading-relaxed text-ink-soft">
              둘 다 꺼 두어도 요청은 보낼 수 있어요. 그 경우 선생님은 위에 적은 요청 내용만 볼 수 있어요.
            </p>
          </Card>

          <Card className="bg-white/70">
            <CardTitle icon={<Phone className="size-5" />} title="지금 바로 도움이 필요하다면" />
            <p className="text-sm leading-relaxed text-ink-soft">
              급하거나 위험한 상황이라면 기다리지 말고 가까운 어른에게 알리거나 아래 번호로 연락해요.
            </p>
            <ul className="mt-3 space-y-2 text-sm">
              <li className="flex items-center justify-between rounded-2xl bg-stone-50 px-4 py-3">
                <span className="text-ink">학교폭력 신고·상담</span>
                <a href="tel:117" className="font-extrabold text-brand-600">117</a>
              </li>
              <li className="flex items-center justify-between rounded-2xl bg-stone-50 px-4 py-3">
                <span className="text-ink">청소년 상담전화</span>
                <a href="tel:1388" className="font-extrabold text-brand-600">1388</a>
              </li>
            </ul>
          </Card>
        </div>
      </div>

      <Notice>
        시연용 프로토타입이라 요청과 공유 설정은 이 브라우저에만 저장돼요. 실제 서비스에 필요한 암호화·접근 권한 관리
        같은 보호 기능은 아직 구현되어 있지 않아요.
      </Notice>
    </div>
  );
}
