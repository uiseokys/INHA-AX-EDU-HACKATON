import {
  ArrowRight,
  Building2,
  CalendarCheck,
  GraduationCap,
  HeartHandshake,
  LineChart,
  ShieldCheck,
  Smile,
  Stethoscope,
} from "lucide-react";
import Link from "next/link";
import { DemoFooter } from "@/components/DemoFooter";
import { Logo } from "@/components/Logo";
import { Chip } from "@/components/ui";

const FEATURES = [
  {
    icon: CalendarCheck,
    tone: "bg-peach-100 text-peach-500",
    title: "매일 쓰는 할 일과 회고",
    body: "오늘의 할 일, 학습 목표, 내일의 작은 목표까지. 감정 기록이 아니어도 매일 열어 볼 이유가 있어요.",
  },
  {
    icon: Smile,
    tone: "bg-butter-100 text-amber-700",
    title: "10초 마음 체크인",
    body: "이모지 하나와 강도만 고르면 끝. 쓰고 싶지 않은 날은 건너뛰어도 괜찮아요.",
  },
  {
    icon: LineChart,
    tone: "bg-brand-100 text-brand-600",
    title: "근거를 보여 주는 변화 분석",
    body: "최근 2주의 흐름과 반복되는 고민 주제를, 근거가 된 기록과 함께 정리해요.",
  },
  {
    icon: Building2,
    tone: "bg-mint-100 text-mint-700",
    title: "상담교사·지원기관 연계",
    body: "학생이 동의한 정보만 상담 선생님께 전달되고, 필요한 전문기관으로 이어져요.",
  },
];

const STEPS = [
  "학생으로 시작해 오늘의 할 일을 확인해요",
  "오늘의 감정을 고르고 기록해요",
  "감정 그래프에 기록이 반영된 걸 확인해요",
  "‘도움 요청’에서 상담 지원을 요청해요",
  "상담교사 화면에서 방금 보낸 요청을 확인해요",
  "지원기관 추천 화면에서 기관을 연결해요",
];

export default function Landing() {
  return (
    <div className="relative flex-1 overflow-hidden">
      {/* 배경 장식 */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-24 -left-20 size-96 animate-float rounded-full bg-brand-200/50 blur-3xl" />
        <div className="absolute top-40 -right-24 size-[28rem] animate-float rounded-full bg-peach-200/50 blur-3xl [animation-delay:-3s]" />
        <div className="absolute bottom-0 left-1/3 size-80 rounded-full bg-mint-200/40 blur-3xl" />
      </div>

      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5 sm:px-6">
        <Logo />
        <Chip className="bg-white/80 text-ink-soft ring-1 ring-stone-200">2026 INHA AX-EDU 해커톤 · 시연용</Chip>
      </header>

      <main className="mx-auto max-w-6xl px-4 sm:px-6">
        <section className="animate-fade-up pt-10 pb-12 text-center sm:pt-16">
          <Chip className="bg-brand-100 text-brand-700">AI 감정 변화 분석 · 조기 발견 · 지원 연계</Chip>
          <h1 className="mx-auto mt-5 max-w-3xl text-4xl leading-tight font-extrabold tracking-tight text-ink sm:text-5xl sm:leading-tight">
            매일의 마음을{" "}
            <span className="bg-linear-to-r from-brand-500 to-peach-400 bg-clip-text text-transparent">쓰담쓰담</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-ink-soft sm:text-lg">
            하루 10초 마음 체크인과 학교생활 회고로 나를 이해하고,
            <br className="hidden sm:block" /> 힘든 날에는 상담 선생님과 전문기관으로 이어지는 마음 기록 서비스
          </p>

          <div className="mx-auto mt-10 grid max-w-3xl gap-4 sm:grid-cols-2">
            <Link
              href="/student"
              className="group rounded-3xl border border-white bg-white/90 p-6 text-left shadow-[0_16px_40px_-16px_rgba(109,89,214,0.35)] transition hover:-translate-y-1 hover:shadow-[0_22px_50px_-16px_rgba(109,89,214,0.45)]"
            >
              <span className="grid size-12 place-items-center rounded-2xl bg-peach-100 text-peach-500">
                <GraduationCap className="size-6" />
              </span>
              <h2 className="mt-4 text-xl font-bold text-ink">학생으로 시작하기</h2>
              <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                오늘의 할 일을 챙기고, 마음을 가볍게 기록해요.
              </p>
              <span className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-brand-600">
                학생 화면 열기 <ArrowRight className="size-4 transition group-hover:translate-x-1" />
              </span>
            </Link>
            <Link
              href="/teacher"
              className="group rounded-3xl border border-white bg-white/90 p-6 text-left shadow-[0_16px_40px_-16px_rgba(56,164,138,0.35)] transition hover:-translate-y-1 hover:shadow-[0_22px_50px_-16px_rgba(56,164,138,0.45)]"
            >
              <span className="grid size-12 place-items-center rounded-2xl bg-mint-100 text-mint-700">
                <Stethoscope className="size-6" />
              </span>
              <h2 className="mt-4 text-xl font-bold text-ink">상담교사 대시보드 보기</h2>
              <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                학생이 공유한 기록과 상담 요청을 확인하고 지원을 연결해요.
              </p>
              <span className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-mint-700">
                교사 화면 열기 <ArrowRight className="size-4 transition group-hover:translate-x-1" />
              </span>
            </Link>
          </div>
        </section>

        <section className="grid gap-4 pb-10 sm:grid-cols-2 lg:grid-cols-4" aria-label="주요 기능">
          {FEATURES.map((f, i) => (
            <article
              key={f.title}
              className="animate-fade-up rounded-3xl border border-white bg-white/75 p-5"
              style={{ animationDelay: `${120 + i * 70}ms` }}
            >
              <span className={`grid size-10 place-items-center rounded-2xl ${f.tone}`}>
                <f.icon className="size-5" />
              </span>
              <h3 className="mt-3 text-base font-bold text-ink">{f.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">{f.body}</p>
            </article>
          ))}
        </section>

        <section className="grid gap-4 pb-6 lg:grid-cols-5">
          <div className="rounded-3xl border border-white bg-white/75 p-6 lg:col-span-3">
            <h2 className="flex items-center gap-2 text-base font-bold text-ink">
              <HeartHandshake className="size-5 text-brand-500" /> 이렇게 시연해 보세요
            </h2>
            <ol className="mt-4 grid gap-2.5 sm:grid-cols-2">
              {STEPS.map((s, i) => (
                <li key={s} className="flex items-start gap-3 rounded-2xl bg-cream px-3.5 py-3 text-sm text-ink">
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-brand-500 text-xs font-bold text-white">
                    {i + 1}
                  </span>
                  {s}
                </li>
              ))}
            </ol>
          </div>
          <div className="rounded-3xl border border-white bg-white/75 p-6 lg:col-span-2">
            <h2 className="flex items-center gap-2 text-base font-bold text-ink">
              <ShieldCheck className="size-5 text-mint-500" /> 쓰담이 지키는 원칙
            </h2>
            <ul className="mt-4 space-y-3 text-sm leading-relaxed text-ink-soft">
              <li>
                <strong className="text-ink">진단하지 않아요.</strong> 분석은 자기 이해를 돕는 참고 정보이며, 학교폭력
                여부나 정신건강 상태를 판정하지 않습니다.
              </li>
              <li>
                <strong className="text-ink">학생이 고른 것만 공유해요.</strong> 공유에 동의하지 않은 기록은 상담교사
                화면에 나타나지 않습니다.
              </li>
              <li>
                <strong className="text-ink">낙인찍지 않아요.</strong> ‘위험 학생’ 같은 분류 대신 지원 절차의 단계로만
                표시합니다.
              </li>
            </ul>
          </div>
        </section>
      </main>

      <DemoFooter />
    </div>
  );
}
