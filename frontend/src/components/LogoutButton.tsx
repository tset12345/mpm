"use client";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function LogoutButton() {
  const router = useRouter();

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.replace("/login");
  };

  return (
    <button
      onClick={handleLogout}
      className="ml-auto text-sm text-gray-400 hover:text-red-500 transition-colors"
    >
      로그아웃
    </button>
  );
}
