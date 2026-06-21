"use client";
import { useState } from "react";
import { SAMPLE_MARKETS } from "@/lib/mockData";

interface Props {
  onAnalyze: (
    question: string,
    ticker: string,
    yesPrice: number,
    category: string
  ) => void;
}

const CATEGORY_ICONS: Record<string, string> = {
  financial: "📈",
  culture: "🎬",
  sports: "⚽",
};

export default function MarketInput({ onAnalyze }: Props) {
  const [question, setQuestion] = useState("");
  const [ticker, setTicker] = useState("");

  const handleSample = (m: (typeof SAMPLE_MARKETS)[0]) => {
    setQuestion(m.question);
    setTicker(m.ticker);
  };

  const handleSubmit = () => {
    if (!question.trim()) return;
    const sample = SAMPLE_MARKETS.find((m) => m.ticker === ticker);
    const effectiveTicker = ticker.trim() || "";
    onAnalyze(
      question,
      effectiveTicker,
      sample?.yesPrice ?? 0.5,
      sample?.category ?? "auto"
    );
  };

  const selected = SAMPLE_MARKETS.find((m) => m.ticker === ticker);

  return (
    <div className="flex flex-col gap-10 fade-in-up">
      {/* Hero */}
      <div className="text-center pt-4">
        <div className="inline-flex items-center gap-2 bg-teal-500/10 border border-teal-500/20 rounded-full px-4 py-1.5 text-xs text-teal-400 font-medium mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
          Multi-agent prediction market intelligence
        </div>
        <h1 className="text-5xl font-bold text-white tracking-tight mb-3">
          Signal<span className="text-teal-400">Forge</span>
        </h1>
        <p className="text-zinc-400 text-lg max-w-lg mx-auto leading-relaxed">
          Research agents collect evidence, compress it, and execute trades on Kalshi — automatically.
        </p>
      </div>

      {/* Input card */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <label className="text-zinc-400 text-xs font-semibold uppercase tracking-wider">
            Market Question
          </label>
          <textarea
            className="bg-zinc-800/60 border border-zinc-700/60 rounded-xl px-4 py-3 text-white placeholder-zinc-600 resize-none focus:outline-none focus:border-teal-500/60 focus:bg-zinc-800 transition text-sm leading-relaxed"
            rows={2}
            placeholder="e.g. Will the Fed raise rates in July 2026?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
          />
        </div>
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="text-zinc-400 text-xs font-semibold uppercase tracking-wider">
              Kalshi Ticker
            </label>
            <span className="text-zinc-600 text-xs">Optional — leave blank for custom questions</span>
          </div>
          <input
            className="bg-zinc-800/60 border border-zinc-700/60 rounded-xl px-4 py-3 text-white placeholder-zinc-600 focus:outline-none focus:border-teal-500/60 focus:bg-zinc-800 transition font-mono text-sm"
            placeholder="e.g. FED-RATES-JUL26 (leave blank to ask any question)"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
          />
        </div>
      </div>

      {/* Sample markets */}
      <div>
        <p className="text-zinc-500 text-xs font-semibold uppercase tracking-wider mb-3">
          Sample Markets
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {SAMPLE_MARKETS.map((m) => {
            const isSelected = ticker === m.ticker;
            return (
              <button
                key={m.ticker}
                onClick={() => handleSample(m)}
                className={`text-left p-4 rounded-xl border transition-all group ${
                  isSelected
                    ? "border-teal-500/60 bg-teal-500/8 shadow-lg shadow-teal-500/5"
                    : "border-zinc-800 bg-zinc-900 hover:border-zinc-600 hover:bg-zinc-800/60"
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="text-lg">{CATEGORY_ICONS[m.category] ?? "🔎"}</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                    isSelected ? "bg-teal-500/20 text-teal-300" : "bg-zinc-800 text-zinc-500"
                  }`}>
                    YES {(m.yesPrice * 100).toFixed(0)}¢
                  </span>
                </div>
                <p className="text-sm text-zinc-200 leading-snug mb-2 group-hover:text-white transition">
                  {m.question}
                </p>
                <p className="text-xs text-zinc-600 font-mono">{m.ticker}</p>
              </button>
            );
          })}
        </div>
      </div>

      <button
        onClick={handleSubmit}
        disabled={!question.trim()}
        className="w-full py-4 rounded-xl bg-teal-500 hover:bg-teal-400 active:bg-teal-600 disabled:opacity-20 disabled:cursor-not-allowed text-black font-bold text-base transition-all shadow-lg shadow-teal-500/20 hover:shadow-teal-400/30 flex items-center justify-center gap-2"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M2 8h10M8 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Run Analysis
      </button>

      {/* Tech stack badges */}
      <div className="flex items-center justify-center gap-4 text-xs text-zinc-600 pb-2">
        {["Fetch.ai uAgents", "Kalshi API", "Claude", "Context Compression"].map((t) => (
          <span key={t} className="flex items-center gap-1.5">
            <span className="w-1 h-1 rounded-full bg-zinc-700" />
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}
