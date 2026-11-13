"use client";

import { CheckCircle2, NotebookPen, PencilLine } from "lucide-react";
import { useState } from "react";
import { btn, Card, CardTitle, cn, field } from "@/components/ui";
import { useApp } from "@/lib/store";

const MOMENTS = ["수업", "친구", "급식", "동아리", "체육", "시험·과제", "쉬는 시간", "방과 후", "가족", "혼자만의 시간"];

/** 오늘의 학교생활 회고: 기억에 남는 일 · 달성한 목표 · 내일의 작은 목표 */
export function ReflectionCard() {
  const { state, today, update } = useApp();
  const saved = state.reflections.find((r) => r.date === today);
  const doneTodos = state.todos.filter((t) => t.done && t.date === today);

  const [editing, setEditing] = useState(false);
  const [moments, setMoments] = useState<string[]>(saved?.moments ?? []);
  const [goal, setGoal] = useState(saved?.tomorrowGoal ?? "");

  const toggle = (m: string) => setMoments((cur) => (cur.includes(m) ? cur.filter((x) => x !== m) : [...cur, m]));
  const save = () => {
    update((s) => ({
      ...s,
      reflections: [...s.reflections.filter((r) => r.date !== today), { date: today, moments, tomorrowGoal: goal.trim() }],
    }));
    setEditing(false);
  };

  const title = (
    <CardTitle
      icon={<NotebookPen className="size-5" />}
      title="오늘의 학교생활 회고"
      hint="하루를 가볍게 돌아보고, 내일의 나에게 목표 하나를 남겨요."
    />
  );

  if (saved && !editing) {
    return (
      <Card>
        {title}
        <div className="animate-pop space-y-3 rounded-3xl bg-mint-50 p-5">
          <p className="flex items-center gap-2 text-sm font-bold text-mint-700">
            <CheckCircle2 className="size-5" /> 오늘의 회고를 남겼어요
          </p>
          {saved.moments.length > 0 && (
            <p className="text-sm text-ink">
              <span className="text-ink-soft">기억에 남는 일 · </span>
              {saved.moments.join(", ")}
            </p>
          )}
          <p className="text-sm text-ink">
            <span className="text-ink-soft">오늘 해낸 일 · </span>
            {doneTodos.length}개
          </p>
          {saved.tomorrowGoal ? (
            <p className="rounded-2xl bg-white px-4 py-3 text-sm text-ink">
              <span className="block text-[11px] font-bold text-mint-700">내일의 작은 목표</span>
              🎯 {saved.tomorrowGoal}
              <span className="mt-1 block text-xs text-ink-soft">내일 접속하면 이 목표를 가장 먼저 보여 드릴게요.</span>
            </p>
          ) : (
            <p className="text-xs text-ink-soft">내일의 목표는 비워 두었어요.</p>
          )}
        </div>
        <button type="button" onClick={() => setEditing(true)} className={cn(btn.ghost, "mt-3 w-full")}>
          <PencilLine className="size-4" /> 회고 고치기
        </button>
      </Card>
    );
  }

  return (
    <Card>
      {title}
      <div className="space-y-5">
        <fieldset>
          <legend className="mb-2 text-sm font-semibold text-ink">오늘 기억에 남는 일</legend>
          <div className="flex flex-wrap gap-2">
            {MOMENTS.map((m) => {
              const on = moments.includes(m);
              return (
                <button
                  key={m}
                  type="button"
                  onClick={() => toggle(m)}
                  aria-pressed={on}
                  className={cn(
                    "rounded-full px-3.5 py-2 text-sm font-semibold transition",
                    on ? "bg-brand-500 text-white shadow-sm" : "bg-stone-100 text-ink-soft hover:bg-brand-50 hover:text-brand-700",
                  )}
                >
                  {m}
                </button>
              );
            })}
          </div>
        </fieldset>

        <div>
          <p className="mb-2 text-sm font-semibold text-ink">오늘 달성한 목표</p>
          {doneTodos.length > 0 ? (
            <ul className="space-y-1.5 rounded-2xl bg-stone-50 px-4 py-3">
              {doneTodos.map((t) => (
                <li key={t.id} className="flex items-center gap-2 text-sm text-ink">
                  <CheckCircle2 className="size-4 shrink-0 text-mint-500" /> {t.text}
                </li>
              ))}
            </ul>
          ) : (
            <p className="rounded-2xl bg-stone-50 px-4 py-3 text-sm text-ink-soft">
              아직 완료한 할 일이 없어요. 위의 할 일 목록에서 체크하면 여기에 모여요.
            </p>
          )}
        </div>

        <div>
          <label htmlFor="tomorrow-goal" className="mb-2 block text-sm font-semibold text-ink">
            내일의 작은 목표
          </label>
          <input
            id="tomorrow-goal"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            maxLength={60}
            placeholder="예: 쉬는 시간에 물 한 컵 마시기"
            className={field}
          />
        </div>

        <div className="flex gap-2">
          <button type="button" onClick={save} className={cn(btn.primary, "flex-1")}>
            회고 남기기
          </button>
          {saved && (
            <button type="button" onClick={() => setEditing(false)} className={btn.ghost}>
              취소
            </button>
          )}
        </div>
      </div>
    </Card>
  );
}
