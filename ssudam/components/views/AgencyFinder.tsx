"use client";

import { ArrowLeft, Building2, Check, ChevronDown, Clock, MapPin, Send, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { btn, Card, Chip, cn, field, Notice, PageSkeleton, Toast } from "@/components/ui";
import { analyze } from "@/lib/analysis";
import {
  agencies,
  agencyTypeLabel,
  agencyTypes,
  consentFor,
  getStudent,
  logsFor,
  matchAgencies,
  referralsFor,
  regions,
  requestsFor,
  statusFor,
  students,
  topicLabel,
} from "@/lib/data";
import { teacherView } from "@/lib/privacy";
import { STATUS } from "@/lib/status";
import { newId, useApp } from "@/lib/store";
import type { Agency } from "@/lib/types";

// 학생이 요청할 때 고른 주제 → 분석 주제 id
const REQUEST_TOPIC: Record<string, string> = {
  "친구 관계": "peer",
  학업: "study",
  가족: "family",
  진로: "career",
  "몸과 마음": "health",
};

const TYPE_TONE: Record<string, string> = {
  "wee-class": "bg-peach-100 text-peach-500",
  "wee-center": "bg-brand-100 text-brand-700",
  "youth-center": "bg-mint-100 text-mint-700",
  etc: "bg-sky-100 text-sky-800",
};

export function AgencyFinder() {
  const params = useSearchParams();
  const { ready, state, today, update } = useApp();
  const [studentId, setStudentId] = useState(params.get("student") ?? "");
  const [type, setType] = useState("all");
  const [region, setRegion] = useState("all");
  const [openId, setOpenId] = useState<string | null>(null);
  const [target, setTarget] = useState<Agency | null>(null);
  const [note, setNote] = useState("");
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (!target) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setTarget(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [target]);

  if (!ready) return <PageSkeleton />;

  const student = studentId ? getStudent(studentId) : undefined;

  // 학생이 공유한 기록과 요청 주제에서 추천 근거가 되는 주제를 모읍니다.
  const studentTopics: string[] = [];
  if (student) {
    const view = teacherView(logsFor(student.id, state, today), consentFor(student, state));
    for (const t of analyze(view.logs, today).topics.slice(0, 2)) studentTopics.push(t.id);
    for (const r of requestsFor(student.id, state, today)) {
      const t = REQUEST_TOPIC[r.topic];
      if (t && !studentTopics.includes(t)) studentTopics.push(t);
    }
  }
  const linked = new Set(student ? referralsFor(student.id, state, today).map((r) => r.agencyId) : []);
  const results = matchAgencies(agencies, { type, region }, studentTopics);
  const typeDesc = agencyTypes.find((t) => t.id === type)?.desc;

  const confirm = () => {
    if (!target || !student) return;
    update((s) => ({
      ...s,
      referrals: [...s.referrals, { id: newId("REF"), studentId: student.id, agencyId: target.id, date: today, note: note.trim() }],
      caseStatus: { ...s.caseStatus, [student.id]: "referred" },
      events: {
        ...s.events,
        [student.id]: [...(s.events[student.id] ?? []), { date: today, text: `진행 상태를 ‘${STATUS.referred.label}’(으)로 변경` }],
      },
    }));
    setToast(`${student.name} 학생의 연결 요청을 기록했어요 (시연용)`);
    setTimeout(() => setToast(null), 2600);
    setTarget(null);
    setNote("");
  };

  return (
    <>
    <div className="animate-fade-up space-y-5">
      {student && (
        <Link href={`/teacher/students/${student.id}`} className="inline-flex items-center gap-1 text-sm font-semibold text-ink-soft hover:text-brand-700">
          <ArrowLeft className="size-4" /> {student.name} 학생 상세
        </Link>
      )}

      <header>
        <h1 className="text-2xl font-extrabold text-ink">지원기관 추천</h1>
        <p className="mt-1 text-sm text-ink-soft">지원 유형과 지역을 고르면 조건에 맞는 기관을 보여 드립니다.</p>
      </header>

      <Notice>
        <strong>가상 기관 정보입니다.</strong> 기관명·소개·운영 시간은 시연을 위해 지어낸 것이며 실제 기관과 무관합니다.
        ‘연결 요청’을 눌러도 실제 예약이나 상담 접수는 이루어지지 않습니다.
      </Notice>

      <Card className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label htmlFor="agency-student" className="mb-2 block text-sm font-semibold text-ink">
              연결할 학생
            </label>
            <select id="agency-student" value={studentId} onChange={(e) => setStudentId(e.target.value)} className={field}>
              <option value="">선택 안 함 (기관만 둘러보기)</option>
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · {s.grade}학년 {s.classNo}반 · {STATUS[statusFor(s, state)].label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="agency-region" className="mb-2 block text-sm font-semibold text-ink">
              지역
            </label>
            <select id="agency-region" value={region} onChange={(e) => setRegion(e.target.value)} className={field}>
              <option value="all">전체 지역</option>
              {regions.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
        </div>

        <fieldset>
          <legend className="mb-2 text-sm font-semibold text-ink">지원 유형</legend>
          <div className="flex flex-wrap gap-2">
            {[{ id: "all", label: "전체" }, ...agencyTypes].map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setType(t.id)}
                aria-pressed={type === t.id}
                className={cn(
                  "rounded-full px-3.5 py-2 text-sm font-semibold transition",
                  type === t.id ? "bg-brand-500 text-white shadow-sm" : "bg-stone-100 text-ink-soft hover:bg-brand-50 hover:text-brand-700",
                )}
              >
                {t.label}
              </button>
            ))}
          </div>
          {typeDesc && <p className="mt-2 text-xs text-ink-soft">{typeDesc}</p>}
        </fieldset>

        {student && (
          <p className="flex flex-wrap items-center gap-1.5 rounded-2xl bg-brand-50/70 px-4 py-3 text-sm text-ink">
            <Sparkles className="size-4 text-brand-500" />
            {studentTopics.length > 0 ? (
              <>
                {student.name} 학생의 요청·공유 기록에서 찾은 주제
                {studentTopics.map((t) => (
                  <Chip key={t} className="bg-white text-brand-700">
                    {topicLabel(t)}
                  </Chip>
                ))}
                를 지원하는 기관을 먼저 보여 드립니다.
              </>
            ) : (
              <>{student.name} 학생이 공유한 정보에서 주제를 찾지 못해 조건에 맞는 기관을 모두 보여 드립니다.</>
            )}
          </p>
        )}
      </Card>

      <p className="px-1 text-sm font-semibold text-ink-soft">조건에 맞는 기관 {results.length}곳</p>

      <ul className="grid items-start gap-4 md:grid-cols-2">
        {results.map(({ agency, matchedTopics }) => {
          const isOpen = openId === agency.id;
          const isLinked = linked.has(agency.id);
          return (
            <li key={agency.id}>
              <Card className="transition hover:shadow-[0_16px_36px_-14px_rgba(110,90,200,0.3)]">
                <div className="flex flex-wrap items-center gap-1.5">
                  <Chip className={TYPE_TONE[agency.type]}>{agencyTypeLabel(agency.type)}</Chip>
                  <Chip className="bg-butter-100 text-amber-800">가상 기관</Chip>
                  {matchedTopics.length > 0 && (
                    <Chip className="bg-brand-500 text-white">
                      <Sparkles className="size-3" /> 추천 · {matchedTopics.map(topicLabel).join(", ")}
                    </Chip>
                  )}
                </div>
                <h2 className="mt-3 flex items-center gap-2 text-lg font-bold text-ink">
                  <Building2 className="size-5 shrink-0 text-ink-soft" /> {agency.name}
                </h2>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">{agency.summary}</p>
                <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-soft">
                  <span className="flex items-center gap-1">
                    <MapPin className="size-3.5" /> {agency.region}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="size-3.5" /> {agency.hours}
                  </span>
                </p>

                {isOpen && (
                  <div className="mt-4 animate-fade-up space-y-3 rounded-2xl bg-stone-50 p-4 text-sm">
                    <p className="leading-relaxed text-ink">{agency.description}</p>
                    <div>
                      <p className="mb-1.5 text-xs font-bold text-ink-soft">지원 내용</p>
                      <div className="flex flex-wrap gap-1.5">
                        {agency.services.map((s) => (
                          <Chip key={s} className="bg-white text-ink ring-1 ring-stone-200">
                            {s}
                          </Chip>
                        ))}
                      </div>
                    </div>
                    <p className="text-xs text-ink-soft">
                      주로 다루는 주제: {agency.topics.map(topicLabel).join(", ")} · 상담 방식: {agency.mode.join(", ")}
                    </p>
                  </div>
                )}

                <div className="mt-4 flex gap-2">
                  <button type="button" onClick={() => setOpenId(isOpen ? null : agency.id)} aria-expanded={isOpen} className={cn(btn.outline, "flex-1")}>
                    {isOpen ? "소개 접기" : "기관 소개"} <ChevronDown className={cn("size-4 transition", isOpen && "rotate-180")} />
                  </button>
                  <button
                    type="button"
                    onClick={() => setTarget(agency)}
                    disabled={isLinked}
                    className={cn(btn.primary, "flex-1 px-4 py-2.5", isLinked && "disabled:bg-mint-100 disabled:text-mint-700")}
                  >
                    {isLinked ? (
                      <>
                        <Check className="size-4" /> 연결 요청됨
                      </>
                    ) : (
                      <>
                        <Send className="size-4" /> 연결 요청
                      </>
                    )}
                  </button>
                </div>
              </Card>
            </li>
          );
        })}
      </ul>
      {results.length === 0 && (
        <Card className="text-center text-sm text-ink-soft">조건에 맞는 기관이 없습니다. 지원 유형이나 지역을 바꿔 보세요.</Card>
      )}

    </div>

      {/* 연결 요청 확인 창: 화면 고정 요소라 애니메이션 영역 밖에 둡니다 */}
      {target && (
        <div className="fixed inset-0 z-50 grid place-items-end bg-ink/40 p-0 backdrop-blur-sm sm:place-items-center sm:p-4" onClick={() => setTarget(null)}>
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="referral-title"
            onClick={(e) => e.stopPropagation()}
            className="max-h-[92dvh] w-full max-w-md animate-pop overflow-y-auto rounded-t-3xl bg-white p-6 shadow-2xl sm:rounded-3xl"
          >
            <div className="flex items-start justify-between gap-3">
              <h2 id="referral-title" className="text-lg font-bold text-ink">
                {target.name}에 연결 요청
              </h2>
              <button type="button" onClick={() => setTarget(null)} aria-label="닫기" className="text-stone-400 hover:text-ink">
                <X className="size-5" />
              </button>
            </div>

            <label htmlFor="referral-student" className="mt-4 mb-2 block text-sm font-semibold text-ink">
              연결할 학생
            </label>
            <select id="referral-student" value={studentId} onChange={(e) => setStudentId(e.target.value)} className={field}>
              <option value="">학생을 선택하세요</option>
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · {s.grade}학년 {s.classNo}반
                </option>
              ))}
            </select>

            <label htmlFor="referral-note" className="mt-4 mb-2 block text-sm font-semibold text-ink">
              기관에 전달할 메모 <span className="font-normal text-ink-soft">(선택)</span>
            </label>
            <textarea
              id="referral-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              placeholder="예: 또래 관계 회복 프로그램 참여 문의"
              className={field}
            />

            <p className="mt-3 rounded-2xl bg-butter-50 px-4 py-3 text-xs leading-relaxed text-amber-900/80">
              시연용 기능입니다. 실제 기관으로 정보가 전송되거나 예약·접수가 이루어지지 않으며, 연결 기록만 이 브라우저에
              남습니다. 실제 연계 시에는 학생·보호자 동의 절차가 필요합니다.
            </p>

            <div className="mt-5 flex gap-2">
              <button type="button" onClick={() => setTarget(null)} className={cn(btn.ghost, "flex-1")}>
                취소
              </button>
              <button type="button" onClick={confirm} disabled={!student || linked.has(target.id)} className={cn(btn.primary, "flex-1")}>
                {student && linked.has(target.id) ? "이미 요청함" : "연결 요청 기록하기"}
              </button>
            </div>
          </div>
        </div>
      )}

      <Toast message={toast} />
    </>
  );
}
