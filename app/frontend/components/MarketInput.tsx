"use client";
import { useState } from "react";
import { SAMPLE_MARKETS } from "@/lib/mockData";

interface Props {
  onAnalyze: (question: string, ticker: string, yesPrice: number) => void;
}

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
    onAnalyze(question, ticker || "CUSTOM-MARKET", sample?.yesPrice ?? 0.5);
  };

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-4xl font-bold text-white mb-2">SignalForge</h1>
        <p className="text-zinc-400 text-lg">
          Multi-agent prediction market intelligence · Powered by Fetch.ai &amp; Kalshi
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <label className="text-zinc-300 text-sm font-medium uppercase tracking-wider">
          Market Question
        </label>
        <textarea
          className="bg-zinc-800 border border-zinc-700 rounded-xl p-4 text-white placeholder-zinc-500 resize-none focus:outline-none focus:border-teal-500 transition"
          rows={2}
          placeholder="e.g. Will the Fed raise rates in July 2026?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <input
          className="bg-zinc-800 border border-zinc-700 rounded-xl p-4 text-white placeholder-zinc-500 focus:outline-none focus:border-teal-500 transition"
          placeholder="Kalshi ticker (e.g. FED-RATES-JUL26)"
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
        />
      </div>

      <div>
        <p className="text-zinc-500 text-sm mb-3">Or pick a sample market:</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {SAMPLE_MARKETS.map((m) => (
            <button
              key={m.ticker}
              onClick={() => handleSample(m)}
              className={`text-left p-4 rounded-xl border transition ${
                ticker === m.ticker
                  ? "border-teal-500 bg-teal-500/10 text-white"
                  : "border-zinc-700 bg-zinc-800 text-zinc-300 hover:border-zinc-500"
              }`}
            >
              <p className="text-xs text-zinc-500 mb-1 font-mono">{m.ticker}</p>
              <p className="text-sm leading-snug">{m.question}</p>
              <p className="text-xs mt-2 text-teal-400">YES {(m.yesPrice * 100).toFixed(0)}¢</p>
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={handleSubmit}
        disabled={!question.trim()}
        className="w-full py-4 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-30 disabled:cursor-not-allowed text-black font-bold text-lg transition"
      >
        Run Analysis →
      </button>
    </div>
  );
}