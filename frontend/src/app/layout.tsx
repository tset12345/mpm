import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import AuthProvider from "@/components/AuthProvider";
import LogoutButton from "@/components/LogoutButton";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "MPM - My Portfolio Manager",
  description: "AI 기반 한국 주식 분석 및 포트폴리오 관리",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className={inter.className}>
        <AuthProvider>
          <nav className="border-b bg-white sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-6">
              <Link href="/" className="font-bold text-lg text-blue-600">MPM</Link>
              <Link href="/stocks" className="text-sm text-gray-600 hover:text-gray-900">종목</Link>
              <Link href="/stocks/history" className="text-sm text-gray-600 hover:text-gray-900">히스토리</Link>
              <Link href="/portfolio" className="text-sm text-gray-600 hover:text-gray-900">포트폴리오</Link>
              <Link href="/virtual" className="text-sm text-gray-600 hover:text-gray-900">가상거래</Link>
              <Link href="/market" className="text-sm text-gray-600 hover:text-gray-900">시장</Link>
              <LogoutButton />
            </div>
          </nav>
          <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
