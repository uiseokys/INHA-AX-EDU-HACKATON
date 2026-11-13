"use client";

import { RotateCcw } from "lucide-react";
import { useState } from "react";
import { resetState } from "@/lib/store";

export function DemoFooter() {
  const [done, setDone] = useState(false);
  return (
    <footer className="mx-auto w-full max-w-6xl px-4 pt-6 pb-28 text-xs leading-relaxed text-ink-soft sm:px-6 md:pb-10">
      <div className="flex flex-col gap-3 rounded-3xl bg-white/60 p-4 sm:flex-row sm:items-center sm:justify-between">
        <p>
          시연용 프로토타입입니다. 화면의 학생·기관 정보는 모두 <strong>합성 데이터</strong>이며, 분석 결과는
          진단이나 판정이 아닌 참고 정보입니다. 기록은 이 브라우저에만 저장됩니다.
        </p>
        <button
          type="button"
          onClick={() => {
            resetState();
            setDone(true);
            setTimeout(() => setDone(false), 2000);
          }}
          className="inline-flex shrink-0 items-center gap-1.5 self-start rounded-full border border-stone-200 bg-white px-3 py-1.5 font-semibold text-ink-soft transition hover:border-brand-300 hover:text-brand-700 sm:self-auto"
        >
          <RotateCcw className="size-3.5" />
          {done ? "초기화했어요" : "시연 데이터 초기화"}
        </button>
      </div>
    </footer>
  );
}
