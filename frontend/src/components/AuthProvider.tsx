"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

export const GUEST_STORAGE_KEY = "mpm_guest_mode";
const GUEST_BLOCKED = ["/portfolio", "/virtual"];

type AuthCtx = { session: Session | null; isGuest: boolean; loginAsGuest: () => void };
const AuthContext = createContext<AuthCtx>({ session: null, isGuest: false, loginAsGuest: () => {} });

export function useSession() {
  return useContext(AuthContext);
}

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [isGuest, setIsGuest] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const guestMode = localStorage.getItem(GUEST_STORAGE_KEY) === "true";
    setIsGuest(guestMode);

    supabase.auth.getSession().then(({ data }) => {
      if (data.session) {
        localStorage.removeItem(GUEST_STORAGE_KEY);
        setIsGuest(false);
      }
      setSession(data.session);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, s) => {
      if (s) {
        localStorage.removeItem(GUEST_STORAGE_KEY);
        setIsGuest(false);
      }
      setSession(s);
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (session === undefined) return;
    const hasAuth = !!session || isGuest;
    if (!hasAuth && pathname !== "/login") {
      router.replace("/login");
      return;
    }
    if (hasAuth && pathname === "/login") {
      router.replace("/stocks");
      return;
    }
    if (isGuest && GUEST_BLOCKED.some((p) => pathname.startsWith(p))) {
      router.replace("/stocks");
    }
  }, [session, isGuest, pathname, router]);

  function loginAsGuest() {
    localStorage.setItem(GUEST_STORAGE_KEY, "true");
    setIsGuest(true);
  }

  if (session === undefined) return null;

  return (
    <AuthContext.Provider value={{ session: session ?? null, isGuest, loginAsGuest }}>
      {children}
    </AuthContext.Provider>
  );
}
