"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import { Braces, GripHorizontal, MoreHorizontal, Trash2, X } from "lucide-react";

import type { Widget } from "@/lib/types";


const colors = ["#F2C94C", "#65D1C4", "#7BA2FF", "#C58AF9", "#FF8C7A", "#8FD17F"];


function formatValue(value: unknown, format: Widget["number_format"]): string {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value ?? "—");
  if (format === "compact") {
    return new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(number);
  }
  if (format === "integer") return new Intl.NumberFormat("en", { maximumFractionDigits: 0 }).format(number);
  if (format === "decimal") return new Intl.NumberFormat("en", { maximumFractionDigits: 2 }).format(number);
  if (format === "percent") return `${number.toFixed(1)}%`;
  return new Intl.NumberFormat("en", { maximumFractionDigits: 2 }).format(number);
}


function buildOption(widget: Widget): echarts.EChartsOption {
  const xField = widget.x_field ?? "";
  const yFields = widget.y_fields ?? [];
  const labels = widget.data.map((row) => String(row[xField] ?? ""));
  const common: echarts.EChartsOption = {
    animationDuration: 500,
    color: colors,
    backgroundColor: "transparent",
    textStyle: { color: "#A6ADB9", fontFamily: "Inter, system-ui, sans-serif" },
    tooltip: {
      trigger: widget.chart_type === "pie" ? "item" : "axis",
      backgroundColor: "#171A20",
      borderColor: "#343943",
      textStyle: { color: "#F4F6F8" },
    },
    grid: { left: 46, right: 20, top: 24, bottom: 46, containLabel: false },
  };

  if (widget.chart_type === "pie") {
    const valueField = yFields[0];
    return {
      ...common,
      legend: { bottom: 0, textStyle: { color: "#8F96A3", fontSize: 10 } },
      series: [
        {
          type: "pie",
          radius: ["42%", "70%"],
          center: ["50%", "44%"],
          itemStyle: { borderColor: "#171A20", borderWidth: 3, borderRadius: 5 },
          label: { show: false },
          emphasis: { label: { show: true, color: "#fff", fontWeight: "bold" } },
          data: widget.data.map((row) => ({ name: String(row[xField]), value: Number(row[valueField]) })),
        },
      ],
    };
  }

  if (widget.chart_type === "scatter") {
    const valueField = yFields[0];
    return {
      ...common,
      grid: { left: 54, right: 24, top: 24, bottom: 46 },
      xAxis: {
        type: "value",
        name: xField.replaceAll("_", " "),
        nameTextStyle: { color: "#7F8793" },
        axisLine: { lineStyle: { color: "#343943" } },
        axisLabel: { color: "#7F8793", fontSize: 10 },
        splitLine: { lineStyle: { color: "#242831", type: "dashed" } },
      },
      yAxis: {
        type: "value",
        name: valueField?.replaceAll("_", " "),
        nameTextStyle: { color: "#7F8793" },
        axisLine: { lineStyle: { color: "#343943" } },
        axisLabel: { color: "#7F8793", fontSize: 10 },
        splitLine: { lineStyle: { color: "#242831", type: "dashed" } },
      },
      series: [
        {
          type: "scatter",
          symbolSize: 10,
          data: widget.data.map((row) => [Number(row[xField]), Number(row[valueField])]),
          itemStyle: { color: colors[1], opacity: 0.78 },
        },
      ],
    };
  }

  const axisStyle = {
    axisLine: { lineStyle: { color: "#343943" } },
    axisTick: { show: false },
    axisLabel: { color: "#7F8793", fontSize: 10 },
    splitLine: { lineStyle: { color: "#242831", type: "dashed" as const } },
  };
  const seriesType: "bar" | "line" = widget.chart_type === "bar" ? "bar" : "line";

  return {
    ...common,
    legend: yFields.length > 1 ? { top: 0, textStyle: { color: "#8F96A3" } } : undefined,
    xAxis: {
      type: "category",
      data: labels,
      ...axisStyle,
      axisLabel: { ...axisStyle.axisLabel, rotate: labels.some((label) => label.length > 12) ? 24 : 0 },
    },
    yAxis: { type: "value", ...axisStyle },
    series: yFields.map((field, index) => ({
      name: field.replaceAll("_", " "),
      type: seriesType,
      data: widget.data.map((row) => Number(row[field]) || 0),
      smooth: widget.chart_type === "line" || widget.chart_type === "area",
      symbol: "circle",
      symbolSize: 6,
      showSymbol: widget.data.length < 30,
      areaStyle: widget.chart_type === "area" ? { opacity: 0.16 } : undefined,
      lineStyle: { width: 2.5 },
      itemStyle: { borderRadius: widget.chart_type === "bar" ? [4, 4, 0, 0] : 0 },
      color: colors[index % colors.length],
    })) as echarts.SeriesOption[],
  };
}


function EChart({ widget }: { widget: Widget }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const option = useMemo(() => buildOption(widget), [widget]);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = echarts.init(containerRef.current, undefined, { renderer: "canvas" });
    chart.setOption(option);
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(containerRef.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [option]);

  return <div className="h-full min-h-0 w-full" ref={containerRef} />;
}


function DataTable({ widget }: { widget: Widget }) {
  const columns = Object.keys(widget.data[0] ?? {});
  return (
    <div className="h-full overflow-auto rounded-xl border border-[#262b33]">
      <table className="w-full border-collapse text-left text-xs">
        <thead className="sticky top-0 z-10 bg-[#1b1e24] text-[10px] uppercase tracking-[0.12em] text-[#858d99]">
          <tr>
            {columns.map((column) => <th className="px-3 py-3 font-semibold" key={column}>{column.replaceAll("_", " ")}</th>)}
          </tr>
        </thead>
        <tbody>
          {widget.data.map((row, index) => (
            <tr className="border-t border-[#252a31] text-[#c7ccd4] hover:bg-[#1a1e23]" key={index}>
              {columns.map((column) => <td className="whitespace-nowrap px-3 py-2.5" key={column}>{String(row[column] ?? "—")}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


export function ChartWidget({ widget, onRemove }: { widget: Widget; onRemove: () => void }) {
  const [showSql, setShowSql] = useState(false);
  const scalar = widget.data[0]?.[widget.value_field ?? "value"];

  return (
    <article className="group relative flex h-full flex-col overflow-hidden rounded-2xl border border-[#262b33] bg-[#14171c] shadow-[0_14px_40px_rgba(0,0,0,0.16)] transition hover:border-[#343a44]">
      <header className="drag-handle relative z-10 flex shrink-0 cursor-move items-start justify-between px-4 pb-1 pt-3.5">
        <div className="min-w-0">
          <h2 className={`${widget.chart_type === "kpi" ? "line-clamp-2 leading-4" : "truncate"} text-[13px] font-semibold tracking-tight text-[#f0f2f5]`}>{widget.title}</h2>
          {widget.description && <p className="mt-0.5 truncate text-[10px] text-[#747c88]">{widget.description}</p>}
        </div>
        <div className="flex items-center gap-0.5 pl-2 text-[#68707c] opacity-0 transition group-hover:opacity-100">
          {widget.sql && (
            <button aria-label="View SQL" className="rounded-md p-1.5 hover:bg-[#252a31] hover:text-[#f2c94c]" onClick={() => setShowSql(true)} type="button"><Braces size={14} /></button>
          )}
          <button aria-label="Remove widget" className="rounded-md p-1.5 hover:bg-[#352326] hover:text-[#ff8181]" onClick={onRemove} type="button"><Trash2 size={14} /></button>
          <MoreHorizontal size={15} />
        </div>
      </header>

      <div className="min-h-0 flex-1 px-3 pb-3 pt-1">
        {widget.chart_type === "kpi" ? (
          <div className="flex h-full min-h-0 items-center justify-between gap-3 px-1">
            <div className="min-w-0 truncate text-[clamp(1.9rem,3vw,3rem)] font-semibold leading-none tracking-[-0.05em] text-white">
              {formatValue(scalar, widget.number_format)}
            </div>
            <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-[#f2c94c]/10 text-[#f2c94c]"><GripHorizontal size={17} /></div>
          </div>
        ) : widget.chart_type === "table" ? (
          <DataTable widget={widget} />
        ) : (
          <EChart widget={widget} />
        )}
      </div>

      {showSql && (
        <div className="absolute inset-0 z-20 flex flex-col bg-[#111419]/98 p-4 backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#f2c94c]">Generated SQL</span>
            <button aria-label="Close SQL" className="rounded-md p-1 text-[#89919d] hover:bg-[#252a31] hover:text-white" onClick={() => setShowSql(false)} type="button"><X size={16} /></button>
          </div>
          <pre className="mt-3 min-h-0 flex-1 overflow-auto whitespace-pre-wrap rounded-xl border border-[#292e36] bg-[#0c0e11] p-3 text-[10px] leading-5 text-[#aeb5c0]">{widget.sql}</pre>
        </div>
      )}
    </article>
  );
}
