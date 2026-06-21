"use client";
import { useEffect, useState } from "react";
import { AgentState, AnalysisResult, buildMockResult } from "@/lib/mockData";

interface Props {
  question: string;
  ticker: string;
  yesPrice: number;
  onComplete: (result: AnalysisResult) => void;
}

const AGENTS: Omit<AgentState, "status" | "chunks" | "rawTokens">[] = [
  { id: "financial", label: "Financial Research Agent", icon: "📈" },
  { id: "culture", label: "Culture Web Agent", icon: "🌐" },
  { id: "sports", label: "Sports Video Agent", icon: "⚽" },
  { id: "politics", label: "Politics News Agent", icon: "📰" },
];

const STATUS_LABEL: Record<AgentState["status"], string> = {
  idle: "Waiting",
  processing: "Collecting evidence...",
  done: "Done",
  error: "Error",
};

export default function PipelineView({ question, ticker, yesPrice, onComplete }: Props) {
  const [agents, setAgents] = useState<AgentState[]>(
    AGENTS.map((a) => ({ ...a, status: "idle", chunks: 0, rawTokens: 0 }))
  );
  const [phase, setPhase] = useState<"agents" | "compressing" | "deciding" | "done">("agents");
  const [rawTotal, setRawTotal] = useState(0);
  const [compressedTokens, setCompressedTokens] = useState(0);

  useEffect(() => {
    const delays = [300, 800, 1400, 1900];

    delays.forEach((delay, i) => {
      setTimeout(() => {
        setAgents((prev) =>
          prev.map((a, idx) => (idx === i ? { ...a, status: "processing" } : a))
        );
        setTimeout(() => {
          const chunks = Math.floor(8 + Math.random() * 20);
          const tokens = Math.floor(2500 + Math.random() * 5000);
          setAgents((prev) =>
            prev.map((a, idx) =>
              idx === i ? { ...a, status: "done", chunks, rawTokens: tokens } : a
            )
          );
          setRawTotal((t) => t + tokens);
        }, 1200 + Math.random() * 800);
      }, delay);
    });

    // After all agents done → compress
    setTimeout(() => {
      setPhase("compressing");
      setTimeout(() => {
        const compressed = Math.floor(1800 + Math.random() * 600);
        setCompressedTokens(compressed);
        setPhase("deciding");
        setTimeout(() => {
          setPhase("done");
          onComplete(buildMockResult(yesPrice));
        }, 1500);
      }, 1800);
    }, 5500);
  }, []);

  const allDone = agents.every((a) => a.status === "done");

  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="text-zinc-500 text-xs font-mono mb-1">{ticker}</p>
        <h2 className="text-white text-xl font-semibold">{question}</h2>
      </div>

      {/* Agent cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {agents.map((a) => (
          <div
            key={a.id}
            className={`rounded-xl border p-4 transition-all ${
              a.status === "done"
                ? "border-teal-500 bg-teal-500/5"
                : a.status === "processing"
                ? "border-yellow-500 bg-yellow-500/5"
                : "border-zinc-700 bg-zinc-800 opacity-50"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-lg">{a.icon}</span>
              <span
                className={`text-xs font-mono px-2 py-0.5 rounded-full ${
                  a.status === "done"
                    ? "bg-teal-500/20 text-teal-300"
                    : a.status === "processing"
                    ? "bg-yellow-500/20 text-yellow-300"
                    : "bg-zinc-700 text-zinc-500"
                }`}
              >
                {a.status === "processing" && (
                  <span className="inline-block mr-1 animate-spin">⟳</span>
                )}
                {STATUS_LABEL[a.status]}
              </span>
            </div>
            <p className="text-sm text-zinc-200">{a.label}</p>
            {a.status === "done" && (
              <p className="text-xs text-zinc-500 mt-1">
                {a.chunks} chunks · {a.rawTokens.toLocaleString()} tokens
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Compression step */}
      {(phase === "compressing" || phase === "deciding" || phase === "done") && (
        <div
          className={`rounded-xl border p-5 transition-all ${
            phase === "compressing"
              ? "border-yellow-500 bg-yellow-500/5"
              : "border-teal-500 bg-teal-500/5"
          }`}
        >
          <div className="flex items-center gap-3 mb-3">
            <span className="text-lg">🗜️</span>
            <span className="text-white font-medium">Context Compression</span>
            {phase === "compressing" && (
              <span className="text-xs text-yellow-300 font-mono animate-pulse">Running...</span>
            )}
          </div>
          {phase !== "compressing" && rawTotal > 0 && (
            <div className="flex items-center gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-zinc-300">{rawTotal.toLocaleString()}</p>
                <p className="text-xs text-zinc-500">raw tokens</p>
              </div>
              <div className="text-zinc-500 text-2xl">→</div>
              <div className="text-center">
                <p className="text-2xl font-bold text-teal-400">{compressedTokens.toLocaleString()}</p>
                <p className="text-xs text-zinc-500">compressed</p>
              </div>
              <div className="ml-auto text-center">
                <p className="text-2xl font-bold text-teal-300">
                  {(rawTotal / compressedTokens).toFixed(1)}x
                </p>
                <p className="text-xs text-zinc-500">reduction</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Decision step */}
      {(phase === "deciding" || phase === "done") && (
        <div
          className={`rounded-xl border p-5 transition-all ${
            phase === "deciding"
              ? "border-yellow-500 bg-yellow-500/5"
              : "border-teal-500 bg-teal-500/5"
          }`}
        >
          <div className="flex items-center gap-3">
            <span className="text-lg">🤖</span>
            <span className="text-white font-medium">Decision Agent (Claude)</span>
            {phase === "deciding" && (
              <span className="text-xs text-yellow-300 font-mono animate-pulse">Reasoning...</span>
            )}
            {phase === "done" && (
              <span className="text-xs text-teal-300 font-mono">Complete</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}