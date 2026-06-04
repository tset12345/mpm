"use client";
import { useState } from "react";
import dynamic from "next/dynamic";

const MarketDashboard = dynamic(() => import("@/components/market/MarketDashboard"), { ssr: false });
const TreemapHeatmap = dynamic(() => import("@/components/market/TreemapHeatmap"), { ssr: false });

type Tab = "dashboard" | "heatmap";

export default function MarketPage() {
  const [tab, setTab] = useState<Tab>("dashboard");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">시장 현황</h1>
      </div>

      <div className="flex border-b">
        {([["dashboard", "시장 지표"], ["heatmap", "히트맵"]] as [Tab, string][]).map(([t, label]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}>
            {label}
          </button>
        ))}
      </div>

      {tab === "dashboard" && <MarketDashboard />}
      {tab === "heatmap" && <TreemapHeatmap />}
    </div>
  );
}
