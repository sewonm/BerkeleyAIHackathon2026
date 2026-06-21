"use client";
import { useState } from "react";
import MarketInput from "@/components/MarketInput";
import PipelineView from "@/components/PipelineView";
import ResultsView from "@/components/ResultsView";
import { AnalysisResult } from "@/lib/mockData";

type Step = "input" | "pipeline" | "results";

const STEPS: Step[] = ["input", "pipeline", "results"];

export default function Home() {
  const [step, setStep] = useState<Step>("input");
  const [market, setMarket] = useState({ question: "", ticker: "", yesPrice: 0.5 });
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const handleAnalyze = (question: string, ticker: string, yesPrice: number) => {
    setMarket({ question, ticker, yesPrice });
    setStep("pipeline");
  };

  const handleComplete = (r: AnalysisResult) => {
    setResult(r);
    setStep("results");
  };

  const handleReset = () => {
    setResult(null);
    setStep("input");
  };

  return (
    <main className="min-h-screen bg-zinc-900 text-white">
      <div className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-teal-400 font-bold text-sm">SignalForge</span>
          <span className="text-zinc-600 text-xs">·</span>
          <div className="flex gap-1">
            {STEPS.map((s, i) => (
              <div
                key={s}
                className={`h-1.5 w-8 rounded-full transition-all ${
                  step === s
                    ? "bg-teal-400"
                    : i < STEPS.indexOf(step)
                    ? "bg-teal-700"
                    : "bg-zinc-700"
                }`}
              />
            ))}
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs text-zinc-500">
          <span>Fetch.ai uAgents</span>
          <span>·</span>
          <span>Kalshi API</span>
          <span>·</span>
          <span>Claude</span>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-10">
        {step === "input" && <MarketInput onAnalyze={handleAnalyze} />}
        {step === "pipeline" && (
          <PipelineView
            question={market.question}
            ticker={market.ticker}
            yesPrice={market.yesPrice}
            onComplete={handleComplete}
          />
        )}
        {step === "results" && result && (
          <ResultsView
            result={result}
            question={market.question}
            ticker={market.ticker}
            onReset={handleReset}
          />
        )}
      </div>
    </main>
  );
}
