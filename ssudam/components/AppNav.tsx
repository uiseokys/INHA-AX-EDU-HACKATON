"use client";

import { Building2, ClipboardList, HeartHandshake, Home, LineChart, Repeat } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "./Logo";
import { Chip, cn } from "./ui";

const NAV = {
  student: {
    label: "학생",
    home: "/student",
    switchTo: { href: "/teacher", label: "상담교사 화면" },
    items: [
      { href: "/student", label: "홈", icon: Home },
      { href: "/student/insights", label: "마음 분석", icon: LineChart },
      { href: "/student/support", label: "도움 요청", icon: HeartHandshake },
    ],
  },
  teacher: {
    label: "상담교사",
    home: "/teacher",
    switchTo: { href: "/student", label: "학생 화면" },
    items: [
      { href: "/teacher", label: "요청 현황", icon: ClipboardList },
      { href: "/teacher/agencies", label: "지원기관", icon: Building2 },
    ],
  },
} as const;

export function AppNav({ mode }: { mode: "student" | "teacher" }) {
  const pathname = usePathname();
  const nav = NAV[mode];
  const isActive = (href: string) =>
    href === nav.home
      ? pathname === href || (mode === "teacher" && pathname.startsWith("/teacher/students"))
      : pathname.startsWith(href);

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-white/70 bg-cream/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4 sm:px-6">
          <Link href="/" aria-label="쓰담 처음 화면" className="shrink-0">
            <Logo />
          </Link>
          <Chip className={mode === "student" ? "bg-peach-100 text-peach-500" : "bg-mint-100 text-mint-700"}>
            {nav.label}
          </Chip>
          <nav className="ml-4 hidden items-center gap-1 md:flex" aria-label="주 메뉴">
            {nav.items.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive(item.href) ? "page" : undefined}
                className={cn(
                  "flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold transition",
                  isActive(item.href) ? "bg-white text-brand-700 shadow-sm" : "text-ink-soft hover:bg-white/70 hover:text-ink",
                )}
              >
                <item.icon className="size-4" />
                {item.label}
              </Link>
            ))}
          </nav>
          <Link
            href={nav.switchTo.href}
            className="ml-auto flex items-center gap-1.5 rounded-full border border-stone-200 bg-white px-3.5 py-2 text-xs font-semibold text-ink-soft transition hover:border-brand-300 hover:text-brand-700"
          >
            <Repeat className="size-3.5" />
            {nav.switchTo.label}
          </Link>
        </div>
      </header>

      {/* 모바일 하단 탭 */}
      <nav
        aria-label="주 메뉴"
        className="fixed inset-x-0 bottom-0 z-40 border-t border-stone-200/70 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
      >
        <div className="mx-auto flex max-w-md">
          {nav.items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive(item.href) ? "page" : undefined}
              className={cn(
                "flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-semibold transition",
                isActive(item.href) ? "text-brand-600" : "text-stone-400",
              )}
            >
              <item.icon className="size-5" />
              {item.label}
            </Link>
          ))}
        </div>
      </nav>
    </>
  );
}
