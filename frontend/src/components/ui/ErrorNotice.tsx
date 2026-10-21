"use client";

import { describeError } from "@/lib/errors";

type Props = {
  error: unknown;
  onRetry?: () => void;
  retrying?: boolean;
  className?: string;
};

/** 조회 실패를 사용자에게 알리고 다시 시도할 수 있게 하는 공통 안내. */
export default function ErrorNotice({ error, onRetry, retrying = false, className = "" }: Props) {
  return (
    <div
      role="alert"
      className={`flex items-center justify-between gap-3 text-sm text-red-600 bg-red-50 rounded-lg px-4 py-3 ${className}`}
    >
      <span>{describeError(error)}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          disabled={retrying}
          className="shrink-0 text-xs text-red-700 underline disabled:opacity-40"
        >
          {retrying ? "다시 시도 중..." : "다시 시도"}
        </button>
      )}
    </div>
  );
}
