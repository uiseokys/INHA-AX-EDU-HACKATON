"use client";

import { Lock, PencilLine, Share2, Smile } from "lucide-react";
import { useState } from "react";
import { btn, Card, CardTitle, Chip, cn, field } from "@/components/ui";
import { ME_ID } from "@/lib/data";
import { EMOTION_LIST, EMOTIONS, INTENSITY_LABELS } from "@/lib/emotions";
import { useApp } from "@/lib/store";
import type { EmotionId } from "@/lib/types";

/** 오늘의 감정 체크인. 이모지 → (강도) → 기록하기, 두세 번의 탭으로 끝납니다. */
export function CheckinCard() {
  const { state, today, update } = useApp();
  const id = `${ME_ID}:${today}`;
  const saved = state.myLogs.find((l) => l.date === today);
  const savedShared = saved ? (state.shareOverrides[id] ?? saved.shared) : false;
  const skipped = state.skipped.includes(today);

  const [editing, setEditing] = useState(false);
  const [emotion, setEmotion] = useState<EmotionId | null>(saved?.emotion ?? null);
  const [intensity, setIntensity] = useState(saved?.intensity ?? 3);
  const [note, setNote] = useState(saved?.note ?? "");
  const [shared, setShared] = useState(savedShared);
  const [noteOpen, setNoteOpen] = useState(!!saved?.note);

  const save = () => {
    if (!emotion) return;
    update((s) => {
      const shareOverrides = { ...s.shareOverrides };
      delete shareOverrides[id];
      return {
        ...s,
        shareOverrides,
        skipped: s.skipped.filter((d) => d !== today),
        myLogs: [
          ...s.myLogs.filter((l) => l.date !== today),
          { id, studentId: ME_ID, date: today, emotion, intensity, note: note.trim() || undefined, shared },
        ],
      };
    });
    setEditing(false);
  };

  const skip = () => update((s) => ({ ...s, skipped: [...s.skipped.filter((d) => d !== today), today] }));

  const title = (
    <CardTitle
      icon={<Smile className="size-5" />}
      title="오늘의 마음 체크인"
      hint="10초면 충분해요. 쓰고 싶지 않은 날은 건너뛰어도 돼요."
    />
  );

  // 1) 이미 기록한 상태
  if (saved && !editing) {
    const e = EMOTIONS[saved.emotion];
    return (
      <Card>
        {title}
        <div className="animate-pop rounded-3xl bg-linear-to-br from-brand-50 to-peach-50 p-5 text-center">
          <p className="text-5xl">{e.emoji}</p>
          <p className="mt-2 text-lg font-bold text-ink">오늘은 {e.label}</p>
          <p className="text-sm text-ink-soft">강도 {saved.intensity} · {INTENSITY_LABELS[saved.intensity]}</p>
          {saved.note && <p className="mx-auto mt-3 max-w-sm rounded-2xl bg-white/80 px-4 py-2.5 text-sm text-ink">“{saved.note}”</p>}
          <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
            <Chip className={savedShared ? "bg-mint-100 text-mint-700" : "bg-white text-ink-soft"}>
              {savedShared ? <Share2 className="size-3" /> : <Lock className="size-3" />}
              {savedShared ? "상담 선생님과 공유" : "나만 보기"}
            </Chip>
            <Chip className="bg-white text-brand-700">그래프에 반영됐어요</Chip>
          </div>
        </div>
        <button type="button" onClick={() => setEditing(true)} className={cn(btn.ghost, "mt-3 w-full")}>
          <PencilLine className="size-4" /> 기록 고치기
        </button>
      </Card>
    );
  }

  // 2) 오늘은 건너뛴 상태
  if (skipped && !editing) {
    return (
      <Card>
        {title}
        <div className="rounded-3xl bg-stone-50 p-6 text-center">
          <p className="text-4xl">🍃</p>
          <p className="mt-2 text-base font-bold text-ink">오늘은 쉬어가요</p>
          <p className="mt-1 text-sm text-ink-soft">
            기록하지 않아도 할 일, 회고, 도움 요청은 그대로 쓸 수 있어요.
          </p>
          <button type="button" onClick={() => setEditing(true)} className={cn(btn.soft, "mt-4")}>
            마음이 바뀌었어요, 기록할래요
          </button>
        </div>
      </Card>
    );
  }

  // 3) 기록 입력
  return (
    <Card>
      {title}
      <fieldset>
        <legend className="mb-2 text-sm font-semibold text-ink">지금 내 마음은?</legend>
        <div className="grid grid-cols-4 gap-2 sm:grid-cols-7">
          {EMOTION_LIST.map((e) => {
            const on = emotion === e.id;
            return (
              <button
                key={e.id}
                type="button"
                onClick={() => setEmotion(e.id)}
                aria-pressed={on}
                className={cn(
                  "flex flex-col items-center gap-1 rounded-2xl border-2 px-1 py-2.5 transition duration-200",
                  on
                    ? "-translate-y-1 border-brand-400 bg-brand-50 shadow-md"
                    : "border-transparent bg-stone-50 hover:-translate-y-0.5 hover:bg-brand-50/60",
                )}
              >
                <span className={cn("text-3xl transition duration-200", on && "scale-110")}>{e.emoji}</span>
                <span className={cn("text-[11px] font-semibold", on ? "text-brand-700" : "text-ink-soft")}>{e.label}</span>
              </button>
            );
          })}
        </div>
      </fieldset>

      {emotion && (
        <div className="mt-5 animate-fade-up space-y-4">
          <fieldset>
            <legend className="mb-2 flex w-full items-center justify-between text-sm font-semibold text-ink">
              얼마나 강하게 느꼈나요?
              <span className="text-xs font-semibold text-brand-600">{INTENSITY_LABELS[intensity]}</span>
            </legend>
            <div className="flex items-center justify-between gap-2 rounded-2xl bg-stone-50 px-4 py-3">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setIntensity(n)}
                  aria-pressed={intensity === n}
                  aria-label={`강도 ${n} (${INTENSITY_LABELS[n]})`}
                  className="grid size-11 place-items-center"
                >
                  <span
                    className={cn(
                      "grid place-items-center rounded-full text-xs font-bold transition-all duration-200",
                      n <= intensity ? "bg-brand-400 text-white" : "bg-white text-stone-400 ring-1 ring-stone-200",
                    )}
                    style={{ width: 20 + n * 4, height: 20 + n * 4 }}
                  >
                    {n}
                  </span>
                </button>
              ))}
            </div>
          </fieldset>

          {noteOpen ? (
            <div>
              <label htmlFor="checkin-note" className="mb-2 block text-sm font-semibold text-ink">
                오늘 있었던 일 <span className="font-normal text-ink-soft">(선택)</span>
              </label>
              <textarea
                id="checkin-note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={2}
                maxLength={200}
                placeholder="한두 줄이면 충분해요"
                className={field}
              />
            </div>
          ) : (
            <button type="button" onClick={() => setNoteOpen(true)} className="text-sm font-semibold text-brand-600 hover:underline">
              + 오늘 있었던 일 한 줄 남기기 (선택)
            </button>
          )}

          <label className="flex cursor-pointer items-center justify-between gap-3 rounded-2xl bg-stone-50 px-4 py-3">
            <span className="text-sm text-ink">
              <span className="font-semibold">이 기록을 상담 선생님과 공유</span>
              <span className="block text-xs text-ink-soft">끄면 나만 볼 수 있어요. 나중에 바꿀 수 있어요.</span>
            </span>
            <input type="checkbox" checked={shared} onChange={(e) => setShared(e.target.checked)} className="peer sr-only" />
            <span className="relative h-6 w-11 shrink-0 rounded-full bg-stone-300 transition peer-checked:bg-mint-400 peer-focus-visible:ring-4 peer-focus-visible:ring-brand-100 after:absolute after:top-0.5 after:left-0.5 after:size-5 after:rounded-full after:bg-white after:shadow after:transition peer-checked:after:translate-x-5" />
          </label>
        </div>
      )}

      <div className="mt-5 flex flex-col gap-2 sm:flex-row">
        <button type="button" onClick={save} disabled={!emotion} className={cn(btn.primary, "flex-1")}>
          {emotion ? `${EMOTIONS[emotion].emoji} 기록하기` : "감정을 골라 주세요"}
        </button>
        {saved ? (
          <button type="button" onClick={() => setEditing(false)} className={btn.ghost}>
            취소
          </button>
        ) : (
          <button type="button" onClick={skip} className={btn.ghost}>
            오늘은 건너뛰기
          </button>
        )}
      </div>
    </Card>
  );
}
