"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "@/components/AuthProvider";
import LogoutButton from "@/components/LogoutButton";

const ALL_TABS = [
  { href: "/stocks", label: "종목" },
  { href: "/stocks/history", label: "히스토리" },
  { href: "/portfolio", label: "포트폴리오" },
  { href: "/virtual", label: "가상거래" },
  { href: "/market", label: "시장" },
];

const GUEST_HREFS = new Set(["/stocks", "/stocks/history", "/market"]);

export default function NavBar() {
  const { isGuest } = useSession();
  const pathname = usePathname();
  const tabs = isGuest ? ALL_TABS.filter((t) => GUEST_HREFS.has(t.href)) : ALL_TABS;

  if (pathname === "/login") return null;

  return (
    <nav className="border-b bg-white sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-6">
        <Link href="/" className="font-bold text-lg text-blue-600">MPM</Link>
        {tabs.map((t) => (
          <Link key={t.href} href={t.href} className="text-sm text-gray-600 hover:text-gray-900">
            {t.label}
          </Link>
        ))}
        <LogoutButton />
      </div>
    </nav>
  );
}
