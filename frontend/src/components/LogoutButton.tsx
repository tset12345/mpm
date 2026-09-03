"use client";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useSession, GUEST_STORAGE_KEY } from "@/components/AuthProvider";

export default function LogoutButton() {
  const router = useRouter();
  const { isGuest } = useSession();

  const handleLogout = async () => {
    if (isGuest) {
      localStorage.removeItem(GUEST_STORAGE_KEY);
    } else {
      await supabase.auth.signOut();
    }
    router.replace("/login");
  };

  return (
    <button
      onClick={handleLogout}
      className="ml-auto text-sm text-gray-400 hover:text-red-500 transition-colors"
    >
      {isGuest ? "로그인" : "로그아웃"}
    </button>
  );
}
