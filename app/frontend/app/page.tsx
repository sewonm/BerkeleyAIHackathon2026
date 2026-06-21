"use client";
import { useState } from "react";
import MarketInput from "@/components/MarketInput";
import PipelineView from "@/components/PipelineView";
import ResultsView from "@/components/ResultsView";
import { AnalysisResult } from "@/lib/mockData";
import { BridgeAgent, BridgeResponse, ExecutionResult } from "@/lib/api";

type Step = "input" | "pipeline" | "results";

const STEPS: Step[] = ["input", "pipeline", "results"];
const STEP_LABELS = ["Market", "Analysis", "Decision"];

export default function Home() {
  const [step, setStep] = useState<Step>("input");
  const [market, setMarket] = useState({
    question: "",
    ticker: "",
    yesPrice: 0.5,
    category: "auto",
  });
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [agents, setAgents] = useState<BridgeAgent[]>([]);
  const [execution, setExecution] = useState<ExecutionResult | undefined>(undefined);
  const [cacheHit, setCacheHit] = useState<boolean | undefined>(undefined);
  const [elapsedSeconds, setElapsedSeconds] = useState<number | undefined>(undefined);

  const handleAnalyze = (
    question: string,
    ticker: string,
    yesPrice: number,
    category: string
  ) => {
    setMarket({ question, ticker, yesPrice, category });
    setStep("pipeline");
  };

  const handleComplete = (data: BridgeResponse) => {
    setResult(data.result);
    setAgents(data.agents);
    setExecution(data.execution);
    setCacheHit(data.cacheHit);
    setElapsedSeconds(data.elapsedSeconds);
    setStep("results");
  };

  const handleReset = () => {
    setResult(null);
    setAgents([]);
    setExecution(undefined);
    setCacheHit(undefined);
    setElapsedSeconds(undefined);
    setStep("input");
  };

  const currentStepIndex = STEPS.indexOf(step);

  return (
    <main className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <header className="border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-teal-500 flex items-center justify-center">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M7 1L13 4V10L7 13L1 10V4L7 1Z" stroke="black" strokeWidth="1.5" strokeLinejoin="round"/>
                <circle cx="7" cy="7" r="2" fill="black"/>
              </svg>
            </div>
            <button onClick={handleReset} className="text-white font-bold tracking-tight hover:text-teal-400 transition">SignalForge</button>
            <span className="text-zinc-600 text-xs hidden sm:block">by Quorum</span>
          </div>

          {/* Step indicator */}
          <nav className="flex items-center gap-1">
            {STEPS.map((s, i) => (
              <div key={s} className="flex items-center gap-1">
                <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-all ${
                  step === s
                    ? "bg-teal-500/20 text-teal-300 border border-teal-500/30"
                    : i < currentStepIndex
                    ? "text-zinc-400"
                    : "text-zinc-600"
                }`}>
                  <span className={`w-4 h-4 rounded-full flex items-center justify-center text-xs ${
                    i < currentStepIndex ? "bg-teal-600 text-black" : step === s ? "bg-teal-500 text-black" : "bg-zinc-700 text-zinc-500"
                  }`}>
                    {i < currentStepIndex ? "✓" : i + 1}
                  </span>
                  <span className="hidden sm:block">{STEP_LABELS[i]}</span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`w-4 h-px ${i < currentStepIndex ? "bg-teal-700" : "bg-zinc-800"}`} />
                )}
              </div>
            ))}
          </nav>

          <div className="flex items-center gap-2 text-xs text-zinc-600">
            <span className="hidden md:flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse" />
              Live
            </span>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-10">
        {step === "input" && <MarketInput onAnalyze={handleAnalyze} />}
        {step === "pipeline" && (
          <PipelineView
            question={market.question}
            ticker={market.ticker}
            yesPrice={market.yesPrice}
            category={market.category}
            onComplete={handleComplete}
          />
        )}
        {step === "results" && result && (
          <ResultsView
            result={result}
            agents={agents}
            execution={execution}
            question={market.question}
            ticker={market.ticker}
            cacheHit={cacheHit}
            elapsedSeconds={elapsedSeconds}
            onReset={handleReset}
          />
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-zinc-800/40 mt-20">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between text-xs text-zinc-600">
          <span>SignalForge · Berkeley AI Hackathon 2026</span>
          <div className="flex items-center gap-3">
            <span>Fetch.ai uAgents</span>
            <span>·</span>
            <span>Kalshi API</span>
            <span>·</span>
            <span>Claude</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
