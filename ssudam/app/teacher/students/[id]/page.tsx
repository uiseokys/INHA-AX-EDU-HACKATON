import type { Metadata } from "next";
import { Suspense } from "react";
import { PageSkeleton } from "@/components/ui";
import { TeacherStudent } from "@/components/views/TeacherStudent";
import { students } from "@/lib/data";

export const metadata: Metadata = { title: "학생 상세 · 쓰담" };

// 가상 학생 8명의 상세 화면을 빌드 시점에 미리 만들어 둡니다.
export function generateStaticParams() {
  return students.map((s) => ({ id: s.id }));
}

async function Detail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <TeacherStudent id={id} />;
}

export default function Page({ params }: PageProps<"/teacher/students/[id]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Detail params={params} />
    </Suspense>
  );
}
