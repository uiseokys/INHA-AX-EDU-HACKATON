import type { Metadata } from "next";
import { StudentSupport } from "@/components/views/StudentSupport";

export const metadata: Metadata = { title: "도움 요청 · 쓰담" };

export default function Page() {
  return <StudentSupport />;
}
