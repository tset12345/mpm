/** 로딩 자리표시자. 레이아웃이 튀지 않도록 높이를 직접 지정해 쓴다. */
export default function Skeleton({ className = "h-16" }: { className?: string }) {
  return <div aria-hidden className={`rounded-lg bg-gray-100 animate-pulse ${className}`} />;
}
