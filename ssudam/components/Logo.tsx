import { cn } from "./ui";

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={cn("size-9", className)} aria-hidden="true">
      <defs>
        <linearGradient id="ssudam-logo" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#9f8ef5" />
          <stop offset="1" stopColor="#ffb98f" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="16" fill="url(#ssudam-logo)" />
      {/* 머리를 쓰다듬는 손길 */}
      <path d="M13 19.5c3-7 19-7 22 0" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" fill="none" />
      <circle cx="18.5" cy="27" r="2.3" fill="#fff" />
      <circle cx="29.5" cy="27" r="2.3" fill="#fff" />
      <path d="M19 33.5c2.6 2.6 7.4 2.6 10 0" stroke="#fff" strokeWidth="2.8" strokeLinecap="round" fill="none" />
    </svg>
  );
}

export function Logo({ className, size = "md" }: { className?: string; size?: "md" | "lg" }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark className={size === "lg" ? "size-14" : "size-9"} />
      <span
        className={cn(
          "font-extrabold tracking-tight text-ink",
          size === "lg" ? "text-4xl" : "text-xl",
        )}
      >
        쓰담
      </span>
    </span>
  );
}
