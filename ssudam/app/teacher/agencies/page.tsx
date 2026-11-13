import type { Metadata } from "next";
import { Suspense } from "react";
import { PageSkeleton } from "@/components/ui";
import { AgencyFinder } from "@/components/views/AgencyFinder";

export const metadata: Metadata = { title: "지원기관 추천 · 쓰담" };

export default function Page() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <AgencyFinder />
    </Suspense>
  );
}
