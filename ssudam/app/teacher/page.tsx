import type { Metadata } from "next";
import { TeacherHome } from "@/components/views/TeacherHome";

export const metadata: Metadata = { title: "상담 지원 현황 · 쓰담" };

export default function Page() {
  return <TeacherHome />;
}
