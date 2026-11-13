"use client";

import { Check, ListTodo, Plus, Target, X } from "lucide-react";
import { useState } from "react";
import { Card, CardTitle, Chip, cn, field } from "@/components/ui";
import { relativeLabel } from "@/lib/date";
import { newId, useApp } from "@/lib/store";
import type { Todo } from "@/lib/types";

/** 지난 회고에서 남긴 '내일의 작은 목표'를 다시 보여 주는 영역 */
function PreviousGoal() {
  const { state, today, update } = useApp();
  const prev = state.reflections
    .filter((r) => r.date < today && r.tomorrowGoal)
    .sort((a, b) => b.date.localeCompare(a.date))[0];
  if (!prev) return null;

  const setResult = (goalResult: "done" | "carried") =>
    update((s) => ({
      ...s,
      reflections: s.reflections.map((r) => (r.date === prev.date ? { ...r, goalResult } : r)),
      todos:
        goalResult === "carried"
          ? [...s.todos, { id: newId("todo"), text: prev.tomorrowGoal, done: false, date: today, kind: "goal" }]
          : s.todos,
    }));

  return (
    <div className="mb-4 rounded-2xl bg-linear-to-r from-butter-50 to-peach-50 p-4 ring-1 ring-butter-200/60">
      <p className="text-[11px] font-bold text-amber-800/80">
        {relativeLabel(prev.date, today)}의 내가 남긴 작은 목표
      </p>
      <p className="mt-1 text-sm font-bold text-ink">🎯 {prev.tomorrowGoal}</p>
      {prev.goalResult ? (
        <p className="mt-2 animate-pop text-xs font-semibold text-mint-700">
          {prev.goalResult === "done" ? "해냈어요! 스스로를 쓰담쓰담 👏" : "오늘 할 일에 옮겨 두었어요. 천천히 해봐요."}
        </p>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setResult("done")}
            className="rounded-full bg-white px-3.5 py-1.5 text-xs font-bold text-mint-700 ring-1 ring-mint-200 transition hover:bg-mint-50"
          >
            해냈어요 🎉
          </button>
          <button
            type="button"
            onClick={() => setResult("carried")}
            className="rounded-full bg-white px-3.5 py-1.5 text-xs font-bold text-ink-soft ring-1 ring-stone-200 transition hover:bg-stone-50"
          >
            오늘 할 일에 추가
          </button>
        </div>
      )}
    </div>
  );
}

export function TodoCard() {
  const { state, today, update } = useApp();
  const [text, setText] = useState("");
  const [kind, setKind] = useState<Todo["kind"]>("todo");

  // 오늘 만든 항목 + 이전에 끝내지 못한 항목
  const todos = state.todos.filter((t) => t.date === today || !t.done);
  const doneCount = todos.filter((t) => t.done).length;
  const pct = todos.length ? Math.round((doneCount / todos.length) * 100) : 0;

  const add = () => {
    const value = text.trim();
    if (!value) return;
    update((s) => ({ ...s, todos: [...s.todos, { id: newId("todo"), text: value, done: false, date: today, kind }] }));
    setText("");
  };
  const toggle = (id: string) =>
    update((s) => ({ ...s, todos: s.todos.map((t) => (t.id === id ? { ...t, done: !t.done, date: today } : t)) }));
  const remove = (id: string) => update((s) => ({ ...s, todos: s.todos.filter((t) => t.id !== id) }));

  return (
    <Card>
      <CardTitle
        icon={<ListTodo className="size-5" />}
        title="오늘의 할 일 · 학습 목표"
        hint={todos.length ? `${todos.length}개 중 ${doneCount}개 완료` : "오늘 할 일을 적어 보세요"}
        action={<span className="text-sm font-bold text-brand-600">{pct}%</span>}
      />
      <div className="mb-4 h-2 overflow-hidden rounded-full bg-stone-100">
        <div
          className="h-full rounded-full bg-linear-to-r from-brand-400 to-peach-300 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      <PreviousGoal />

      <ul className="space-y-2">
        {todos.map((t) => (
          <li
            key={t.id}
            className={cn(
              "group flex items-center gap-3 rounded-2xl border px-3.5 py-3 transition",
              t.done ? "border-transparent bg-stone-50" : "border-stone-100 bg-white hover:border-brand-200",
            )}
          >
            <button
              type="button"
              onClick={() => toggle(t.id)}
              aria-pressed={t.done}
              aria-label={`${t.text} ${t.done ? "완료 취소" : "완료"}`}
              className={cn(
                "grid size-6 shrink-0 place-items-center rounded-full border-2 transition",
                t.done ? "border-brand-400 bg-brand-400 text-white" : "border-stone-300 text-transparent hover:border-brand-300",
              )}
            >
              <Check className="size-3.5" strokeWidth={3.5} />
            </button>
            <span className={cn("min-w-0 flex-1 text-sm", t.done ? "text-stone-400 line-through" : "text-ink")}>
              {t.text}
            </span>
            {t.kind === "goal" && <Chip className="bg-mint-50 text-mint-700">학습 목표</Chip>}
            <button
              type="button"
              onClick={() => remove(t.id)}
              aria-label={`${t.text} 삭제`}
              className="text-stone-300 transition hover:text-stone-500 md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100"
            >
              <X className="size-4" />
            </button>
          </li>
        ))}
        {todos.length === 0 && (
          <li className="rounded-2xl bg-stone-50 px-4 py-5 text-center text-sm text-ink-soft">
            아직 할 일이 없어요. 아래에서 하나 추가해 보세요.
          </li>
        )}
      </ul>

      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          add();
        }}
      >
        <button
          type="button"
          onClick={() => setKind(kind === "todo" ? "goal" : "todo")}
          aria-label={`종류 바꾸기 (현재: ${kind === "todo" ? "할 일" : "학습 목표"})`}
          title="할 일 ↔ 학습 목표"
          className={cn(
            "grid size-11 shrink-0 place-items-center rounded-2xl transition",
            kind === "goal" ? "bg-mint-100 text-mint-700" : "bg-stone-100 text-ink-soft",
          )}
        >
          {kind === "goal" ? <Target className="size-5" /> : <ListTodo className="size-5" />}
        </button>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={kind === "goal" ? "학습 목표 추가 (예: 과학 3단원 복습)" : "할 일 추가"}
          aria-label="새 할 일"
          className={cn(field, "py-2.5")}
        />
        <button
          type="submit"
          disabled={!text.trim()}
          aria-label="추가"
          className="grid size-11 shrink-0 place-items-center rounded-2xl bg-brand-500 text-white transition hover:bg-brand-600 disabled:bg-stone-200"
        >
          <Plus className="size-5" />
        </button>
      </form>
    </Card>
  );
}
