import { Suspense } from "react";
import { AppNav } from "@/components/AppNav";
import { DemoFooter } from "@/components/DemoFooter";

export default function StudentLayout({ children }: LayoutProps<"/student">) {
  return (
    <div className="flex-1 bg-linear-to-b from-peach-50/70 via-cream to-brand-50/60">
      <Suspense fallback={<div className="h-16" />}>
        <AppNav mode="student" />
      </Suspense>
      <main className="mx-auto w-full max-w-6xl px-4 pt-6 sm:px-6">{children}</main>
      <DemoFooter />
    </div>
  );
}
