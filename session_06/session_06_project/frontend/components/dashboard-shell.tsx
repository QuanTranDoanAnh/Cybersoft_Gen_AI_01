"use client";

import { useEffect, useMemo, useState } from "react";
import ReactGridLayout, {
  type Layout,
  useContainerWidth,
  verticalCompactor,
} from "react-grid-layout";
import {
  Bell,
  ChevronDown,
  CircleAlert,
  LoaderCircle,
  RefreshCcw,
  Share2,
  Sparkles,
} from "lucide-react";

import { api } from "@/lib/api";
import { useDashboardStore } from "@/lib/store";
import type { MetaResponse } from "@/lib/types";
import { ChartWidget } from "./chart-widget";
import { CopilotBar } from "./copilot-bar";
import { Sidebar } from "./sidebar";


function LoadingDashboard() {
  return (
    <div className="grid grid-cols-12 gap-4">
      {[...Array(8)].map((_, index) => (
        <div
          className={`rounded-2xl border border-[#20242b] bg-[linear-gradient(110deg,#111419_8%,#1c2026_18%,#111419_33%)] bg-[length:200%_100%] [animation:shimmer_1.5s_linear_infinite] ${index < 4 ? "col-span-3 h-32" : "col-span-6 h-72"}`}
          key={index}
        />
      ))}
    </div>
  );
}


export function DashboardShell() {
  const {
    title,
    subtitle,
    widgets,
    loading,
    error,
    copilotMessage,
    setOverview,
    replaceDashboard,
    updateLayout,
    removeWidget,
    reset,
    setLoading,
    setError,
  } = useDashboardStore();
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const { width, containerRef, mounted } = useContainerWidth();

  useEffect(() => {
    Promise.all([api.overview(), api.meta()])
      .then(([dashboard, metadata]) => {
        setOverview(dashboard.title, dashboard.subtitle, dashboard.widgets);
        setMeta(metadata);
      })
      .catch((reason: Error) => setError(reason.message));
  }, [setError, setOverview]);

  const layout = useMemo<Layout>(
    () => widgets.map((widget) => ({ i: widget.id, ...widget.layout, minW: 3, minH: 2 })),
    [widgets],
  );

  const askCopilot = async (prompt: string) => {
    setLoading(true);
    try {
      const response = await api.copilot(prompt);
      replaceDashboard(response.title, response.widgets, response.message);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Copilot request failed");
    }
  };

  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="min-h-screen px-4 pb-16 pt-4 md:px-7 lg:ml-[248px] lg:px-9">
        <header className="mx-auto flex max-w-[1480px] items-center justify-between">
          <div className="flex items-center gap-3 text-xs text-[#7f8793]">
            <span className="text-[#b7bdc7]">My workspace</span>
            <span>/</span>
            <button className="flex items-center gap-1 font-medium text-white" type="button">TV Shows Analytics <ChevronDown size={13} /></button>
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden items-center gap-2 rounded-full border border-[#2c3139] bg-[#13161b] px-3 py-1.5 text-[10px] text-[#8e95a1] sm:flex">
              <span className={`size-1.5 rounded-full ${meta?.copilot_mode === "openai" ? "bg-[#65d1c4]" : "bg-[#f2c94c]"}`} />
              {meta?.copilot_mode === "openai" ? meta.model : "Demo planner"}
            </div>
            <button aria-label="Notifications" className="grid size-9 place-items-center rounded-xl border border-[#292e36] bg-[#13161b] text-[#8e95a1] hover:text-white" type="button"><Bell size={16} /></button>
            <button className="flex h-9 items-center gap-2 rounded-xl bg-[#f2c94c] px-3 text-xs font-semibold text-[#171717] hover:bg-[#f7d764]" type="button"><Share2 size={14} /> Share</button>
          </div>
        </header>

        <div className="mx-auto mt-9 max-w-[1480px]">
          <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
            <div>
              <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#f2c94c]"><Sparkles size={13} /> AI-powered dashboard</div>
              <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white md:text-[38px]">{title}</h1>
              <p className="mt-2 text-sm text-[#858d99]">{subtitle}</p>
            </div>
            <button className="flex h-9 items-center gap-2 self-start whitespace-nowrap rounded-xl border border-[#30353e] bg-[#15181d] px-3 text-xs text-[#aab0ba] transition hover:border-[#565d69] hover:text-white lg:self-auto" onClick={reset} type="button"><RefreshCcw size={14} /> Reset dashboard</button>
          </div>

          <div className="mt-7">
            <CopilotBar disabled={loading} onSubmit={askCopilot} />
          </div>

          {copilotMessage && (
            <div className="animate-float-in mt-4 flex items-start gap-2 rounded-xl border border-[#3e3a28] bg-[#f2c94c]/[0.06] px-4 py-3 text-xs leading-5 text-[#c8c0a2]">
              <Sparkles className="mt-0.5 shrink-0 text-[#f2c94c]" size={14} /> {copilotMessage}
            </div>
          )}
          {error && (
            <div className="mt-4 flex items-start gap-2 rounded-xl border border-[#513033] bg-[#3a1f22]/50 px-4 py-3 text-xs text-[#ffacac]">
              <CircleAlert size={15} /> <span>{error}</span>
            </div>
          )}

          <div className="relative mt-6 min-h-[500px]" ref={containerRef}>
            {loading && widgets.length === 0 ? (
              <LoadingDashboard />
            ) : (
              <>
              {loading && (
                <div className="absolute right-3 top-3 z-20 flex items-center gap-2 rounded-full border border-[#353a43] bg-[#15181d]/95 px-3 py-2 text-[10px] text-[#c8ced7] shadow-xl backdrop-blur">
                  <LoaderCircle className="animate-spin text-[#f2c94c]" size={13} /> Copilot is analyzing your data
                </div>
              )}
              {mounted && (
                <ReactGridLayout
                  compactor={verticalCompactor}
                  dragConfig={{ enabled: true, handle: ".drag-handle" }}
                  gridConfig={{ cols: 12, rowHeight: 34, margin: [14, 14], containerPadding: [0, 0] }}
                  layout={layout}
                  onLayoutChange={(nextLayout) => updateLayout([...nextLayout])}
                  resizeConfig={{ enabled: true, handles: ["se"] }}
                  width={width}
                >
                  {widgets.map((widget) => (
                    <div key={widget.id}>
                      <ChartWidget onRemove={() => removeWidget(widget.id)} widget={widget} />
                    </div>
                  ))}
                </ReactGridLayout>
              )}
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
