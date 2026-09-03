"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { useSession } from "@/components/AuthProvider";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { loginAsGuest } = useSession();

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setLoading(false);
      setError(error.message);
    }
    // 성공 시: AuthProvider의 onAuthStateChange가 세션 감지 → /stocks 리다이렉트
    // setLoading(false) 생략 — 화면 전환 완료까지 "로그인 중..." 유지
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-sm">
        <h1 className="text-2xl font-bold text-blue-600 mb-6 text-center">MPM</h1>
        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <input
            type="email"
            placeholder="이메일"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <input
            type="password"
            placeholder="비밀번호"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 text-white rounded py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "로그인 중..." : "로그인"}
          </button>
        </form>
        <div className="mt-4 pt-4 border-t">
          <button
            type="button"
            onClick={loginAsGuest}
            className="w-full text-gray-500 border border-gray-300 rounded py-2 text-sm font-medium hover:bg-gray-50 transition-colors"
          >
            게스트 입장
          </button>
          <p className="text-xs text-gray-400 text-center mt-2">종목·히스토리·시장 탭 열람 가능</p>
        </div>
      </div>
    </div>
  );
}
