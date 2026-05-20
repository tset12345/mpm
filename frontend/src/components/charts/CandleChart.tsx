"use client";
import { useEffect, useRef } from "react";
import { createChart, IChartApi } from "lightweight-charts";

interface OHLCVData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface CandleChartProps {
  data: OHLCVData[];
  height?: number;
}

export default function CandleChart({ data, height = 300 }: CandleChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: { background: { color: "#ffffff" }, textColor: "#333" },
      grid: { vertLines: { color: "#f0f0f0" }, horzLines: { color: "#f0f0f0" } },
    });
    chartRef.current = chart;

    const series = chart.addCandlestickSeries({
      upColor: "#ef4444",
      downColor: "#3b82f6",
      borderVisible: false,
      wickUpColor: "#ef4444",
      wickDownColor: "#3b82f6",
    });
    series.setData(data);
    chart.timeScale().fitContent();

    return () => chart.remove();
  }, [data, height]);

  return <div ref={containerRef} />;
}
