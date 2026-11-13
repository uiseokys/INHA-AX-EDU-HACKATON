import type { ComponentProps, ReactNode } from "react";

export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

export function Card({ className, ...props }: ComponentProps<"section">) {
  return (
    <section
      className={cn(
        "rounded-3xl border border-white/80 bg-white/90 p-5 shadow-[0_10px_30px_-12px_rgba(110,90,200,0.18)] backdrop-blur sm:p-6",
        className,
      )}
      {...props}
    />
  );
}

export function CardTitle({
  icon,
  title,
  hint,
  action,
}: {
  icon?: ReactNode;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div className="flex min-w-0 items-center gap-2.5">
        {icon && (
          <span className="grid size-9 shrink-0 place-items-center rounded-2xl bg-brand-50 text-brand-600">
            {icon}
          </span>
        )}
        <div className="min-w-0">
          <h2 className="text-base font-bold text-ink">{title}</h2>
          {hint && <p className="mt-0.5 text-xs text-ink-soft">{hint}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

export function Chip({ className, ...props }: ComponentProps<"span">) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap",
        className,
      )}
      {...props}
    />
  );
}

export const btn = {
  primary:
    "inline-flex items-center justify-center gap-2 rounded-2xl bg-brand-500 px-5 py-3 text-sm font-bold text-white shadow-[0_8px_20px_-8px_rgba(109,89,214,0.6)] transition hover:-translate-y-0.5 hover:bg-brand-600 active:translate-y-0 disabled:translate-y-0 disabled:bg-stone-200 disabled:text-stone-400 disabled:shadow-none",
  soft: "inline-flex items-center justify-center gap-2 rounded-2xl bg-brand-50 px-4 py-2.5 text-sm font-semibold text-brand-700 transition hover:bg-brand-100",
  ghost:
    "inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold text-ink-soft transition hover:bg-stone-100 hover:text-ink",
  outline:
    "inline-flex items-center justify-center gap-2 rounded-2xl border border-stone-200 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-brand-300 hover:text-brand-700",
};

export const field =
  "w-full rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-ink placeholder:text-stone-400 transition focus:border-brand-300 focus:outline-none focus:ring-4 focus:ring-brand-100";

/** 시연용·합성 데이터임을 알리는 안내 띠 */
export function Notice({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p
      className={cn(
        "rounded-2xl bg-butter-50 px-4 py-3 text-xs leading-relaxed text-amber-900/80 ring-1 ring-butter-200/70",
        className,
      )}
    >
      {children}
    </p>
  );
}

export function PageSkeleton() {
  return (
    <div className="grid gap-5 lg:grid-cols-2" aria-busy="true" aria-label="불러오는 중">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="h-56 animate-pulse rounded-3xl bg-white/70" />
      ))}
    </div>
  );
}

export function Toast({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div
      role="status"
      className="fixed inset-x-0 bottom-24 z-50 mx-auto w-fit max-w-[90vw] animate-pop rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white shadow-xl md:bottom-10"
    >
      {message}
    </div>
  );
}
