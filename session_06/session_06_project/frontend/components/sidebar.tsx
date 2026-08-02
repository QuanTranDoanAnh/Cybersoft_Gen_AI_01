"use client";

import {
  BarChart3,
  Database,
  Gauge,
  LayoutDashboard,
  PanelLeftClose,
  Settings,
  Sparkles,
} from "lucide-react";


const navigation = [
  { label: "Overview", icon: LayoutDashboard, active: true },
  { label: "Explore", icon: BarChart3 },
  { label: "Datasets", icon: Database },
  { label: "Metrics", icon: Gauge },
];


export function Sidebar() {
  return (
    <aside className="desktop-nav fixed inset-y-0 left-0 z-30 flex w-[248px] flex-col border-r border-[#242831] bg-[#0e1115]/95 px-4 py-5 backdrop-blur-xl">
      <div className="flex items-center gap-3 px-2">
        <div className="grid size-10 place-items-center rounded-xl bg-[#f2c94c] text-[#121212] shadow-[0_0_28px_rgba(242,201,76,0.2)]">
          <Sparkles size={20} strokeWidth={2.5} />
        </div>
        <div>
          <div className="text-[17px] font-semibold tracking-tight">InsightFlow</div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#7e8490]">AI Business Intelligence</div>
        </div>
      </div>

      <div className="mt-9 px-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#666d79]">Workspace</div>
      <nav className="mt-3 space-y-1.5">
        {navigation.map(({ label, icon: Icon, active }) => (
          <button
            className={`flex h-11 w-full items-center gap-3 rounded-xl px-3 text-sm transition ${
              active
                ? "bg-[#1d2026] font-medium text-white shadow-[inset_3px_0_0_#f2c94c]"
                : "text-[#8f96a3] hover:bg-[#16191e] hover:text-white"
            }`}
            key={label}
            type="button"
          >
            <Icon size={18} />
            {label}
          </button>
        ))}
      </nav>

      <div className="mt-auto rounded-2xl border border-[#2b3038] bg-gradient-to-br from-[#191d23] to-[#111419] p-4">
        <div className="flex items-center gap-2 text-xs font-medium text-[#f2c94c]">
          <Sparkles size={14} /> Copilot ready
        </div>
        <p className="mt-2 text-xs leading-5 text-[#858c98]">
          Ask questions and turn your data into dashboard visuals.
        </p>
      </div>

      <div className="mt-3 flex items-center justify-between px-2 py-2 text-[#777e8a]">
        <button className="flex items-center gap-2 text-xs hover:text-white" type="button">
          <Settings size={16} /> Settings
        </button>
        <PanelLeftClose size={16} />
      </div>
    </aside>
  );
}
