import type { Metadata } from "next";
import { StudentInsights } from "@/components/views/StudentInsights";

export const metadata: Metadata = { title: "마음 분석 · 쓰담" };

export default function Page() {
  return <StudentInsights />;
}
