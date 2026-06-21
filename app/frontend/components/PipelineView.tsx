"use client";
import { useEffect, useRef, useState } from "react";
import { analyzeMarket, BridgeAgent, BridgeResponse } from "@/lib/api";

interface Props {
  question: string;
  ticker: string;
  yesPrice: number;
  category: string;
  onComplete: (data: BridgeResponse) => void;
}

// Agents we may show. The bridge returns whichever actually ran; until the
// response arrives they're shown as "processing".
const KNOWN_AGENTS: Omit<BridgeAgent, "status" | "chunks" | "rawTokens">[] = [
  { id: "financial", label: "Financial Research Agent", icon: "📈" },
  { id: "culture", label: "Culture Web Agent", icon: "🌐" },
  { id: "sports", label: "Sports Video Agent", icon: "⚽" },
];

const STATUS_LABEL: Record<BridgeAgent["status"], string> = {
  idle: "Waiting",
  processing: "Collecting evidence...",
  done: "Done",
  error: "No data",
};

type Phase = "agents" | "compressing" | "deciding" | "done" | "error";

export default function PipelineView({
  question,
  ticker,
  yesPrice,
  category,
  onComplete,
}: Props) {
  const [agents, setAgents] = useState<BridgeAgent[]>(
    KNOWN_AGENTS.map((a) => ({ ...a, status: "processing", chunks: 0, rawTokens: 0 }))
  );
  const [phase, setPhase] = useState<Phase>("agents");
  const [rawTotal, setRawTotal] = useState(0);
  const [compressedTokens, setCompressedTokens] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const startedRef = useRef(false);

  useEffect(() => {
    // Guard against double-invocation (React 18+ Strict Mode mounts twice).
    if (startedRef.current) return;
    startedRef.current = true;

    (async () => {
      try {
        const data = await analyzeMarket({ question, ticker, yesPrice, category });

        // Real per-agent results from the live collectors.
        setAgents(data.agents);
        setRawTotal(data.rawTokens);

        // Brief staged reveal so the compression/decision steps read clearly.
        setPhase("compressing");
        setTimeout(() => {
          setCompressedTokens(data.compressedTokens);
          setPhase("deciding");
          setTimeout(() => {
            setPhase("done");
            onComplete(data);
          }, 700);
        }, 600);
      } catch (e) {
        setErrorMsg(e instanceof Error ? e.message : String(e));
        setPhase("error");
        setAgents((prev) => prev.map((a) => ({ ...a, status: "error" })));
      }
    })();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="text-zinc-500 text-xs font-mono mb-1">{ticker}</p>
        <h2 className="text-white text-xl font-semibold">{question}</h2>
      </div>

      {phase === "error" && (
        <div className="rounded-xl border border-red-500 bg-red-500/10 p-4 text-sm text-red-300">
          <p className="font-semibold mb-1">⚠ Could not reach the agent bridge</p>
          <p className="text-red-400/80 break-all">{errorMsg}</p>
          <p className="text-zinc-400 mt-2">
            Start it from the repo root:{" "}
            <code className="font-mono">uvicorn app.bridge_server:app --port 8080</code>
          </p>
        </div>
      )}

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
                : a.status === "error"
                ? "border-zinc-700 bg-zinc-800 opacity-60"
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
          {phase !== "compressing" && rawTotal > 0 && compressedTokens > 0 && (
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
            <span className="text-white font-medium">Decision Agent (heuristic)</span>
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