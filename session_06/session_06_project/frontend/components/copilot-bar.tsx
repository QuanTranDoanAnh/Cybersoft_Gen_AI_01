"use client";

import { FormEvent, useState } from "react";
import { ArrowUp, Sparkles } from "lucide-react";


interface CopilotBarProps {
  disabled: boolean;
  onSubmit: (prompt: string) => Promise<void>;
}


const suggestions = [
  "Top genres by number of shows",
  "Show release trends by year",
  "Which countries produce the most shows?",
];


export function CopilotBar({ disabled, onSubmit }: CopilotBarProps) {
  const [prompt, setPrompt] = useState("");

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    const value = prompt.trim();
    if (!value || disabled) return;
    setPrompt("");
    await onSubmit(value);
  };

  return (
    <div className="relative">
      <form
        className="flex min-h-16 items-center gap-3 rounded-2xl border border-[#343943] bg-[#171a20] p-2 pl-4 shadow-[0_18px_60px_rgba(0,0,0,0.28)] transition focus-within:border-[#f2c94c]/60 focus-within:shadow-[0_18px_60px_rgba(242,201,76,0.06)]"
        onSubmit={submit}
      >
        <Sparkles className="shrink-0 text-[#f2c94c]" size={20} />
        <input
          aria-label="Ask Copilot"
          className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-[#707784]"
          disabled={disabled}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Ask Copilot to analyze data or create a visual..."
          value={prompt}
        />
        <button
          aria-label="Send prompt"
          className="grid size-11 shrink-0 place-items-center rounded-xl bg-[#f2c94c] text-[#161616] transition hover:bg-[#f7d764] disabled:cursor-not-allowed disabled:opacity-40"
          disabled={!prompt.trim() || disabled}
          type="submit"
        >
          <ArrowUp size={18} strokeWidth={2.6} />
        </button>
      </form>
      <div className="mt-3 flex flex-wrap gap-2">
        {suggestions.map((suggestion) => (
          <button
            className="rounded-full border border-[#292e36] bg-[#111419] px-3 py-1.5 text-[11px] text-[#8e95a1] transition hover:border-[#5b5540] hover:text-[#f2c94c]"
            disabled={disabled}
            key={suggestion}
            onClick={() => {
              setPrompt(suggestion);
            }}
            type="button"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}
