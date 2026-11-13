import type { Metadata } from "next";
import { StudentHome } from "@/components/views/StudentHome";

export const metadata: Metadata = { title: "학생 홈 · 쓰담" };

export default function Page() {
  return <StudentHome />;
}
