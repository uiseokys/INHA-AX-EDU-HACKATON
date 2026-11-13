import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "쓰담 · 매일의 마음을 쓰담쓰담",
  description:
    "하루 10초 마음 체크인과 학교생활 회고로 나를 이해하고, 필요할 때 상담 선생님과 지원기관으로 이어지는 교육 AI 서비스 (시연용 프로토타입)",
};

export const viewport: Viewport = {
  themeColor: "#fbf7f1",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className="h-full antialiased">
      <head>
        <link rel="preconnect" href="https://cdn.jsdelivr.net" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
      </head>
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
