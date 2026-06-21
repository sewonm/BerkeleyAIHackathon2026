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

const AGENT_META: Record<string, { label: string; icon: string }> = {
  financial: { label: "Financial Research Agent", icon: "📈" },
  culture:   { label: "Culture Web Agent",        icon: "🌐" },
  sports:    { label: "Sports Video Agent",       icon: "⚽" },
};

type Phase = "agents" | "compressing" | "deciding" | "done" | "error";

function Spinner() {
  return (
    <svg className="animate-spin w-3.5 h-3.5 text-yellow-400" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.2"/>
      <path d="M12 2a10 10 0 0110 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
    </svg>
  );
}

export default function PipelineView({ question, ticker, yesPrice, category, onComplete }: Props) {
  const [dispatchedAgent, setDispatchedAgent] = useState<BridgeAgent | null>(null);
  const [phase, setPhase] = useState<Phase>("agents");
  const [rawTotal, setRawTotal] = useState(0);
  const [compressedTokens, setCompressedTokens] = useState(0);
  const [compressionRatio, setCompressionRatio] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const startedRef = useRef(false);

  // Derive which agent will be dispatched from category hint so we can show it immediately
  const pendingCategory = category && !["auto", "custom", ""].includes(category) ? category : "culture";
  const pendingMeta = AGENT_META[pendingCategory] ?? AGENT_META["culture"];

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    (async () => {
      try {
        const data = await analyzeMarket({ question, ticker, yesPrice, category });
        // Bridge returns exactly one agent now
        const agent = data.agents[0] ?? null;
        setDispatchedAgent(agent);
        setRawTotal(data.rawTokens);
        setPhase("compressing");
        setTimeout(() => {
          setCompressedTokens(data.compressedTokens);
          setCompressionRatio(data.compressionRatio);
          setPhase("deciding");
          setTimeout(() => {
            setPhase("done");
            onComplete(data);
          }, 800);
        }, 700);
      } catch (e) {
        setErrorMsg(e instanceof Error ? e.message : String(e));
        setPhase("error");
      }
    })();
  }, []);

  const agent = dispatchedAgent ?? {
    id: pendingCategory,
    label: pendingMeta.label,
    icon: pendingMeta.icon,
    status: "processing" as const,
    chunks: 0,
    rawTokens: 0,
  };

  return (
    <div className="flex flex-col gap-6 fade-in-up">
      {/* Market header */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
        <p className="text-teal-500 text-xs font-mono mb-1">{ticker}</p>
        <h2 className="text-white text-lg font-semibold leading-snug">{question}</h2>
        <div className="flex items-center gap-2 mt-3">
          <span className="text-xs text-zinc-500">YES price</span>
          <span className="text-sm font-bold text-white">{(yesPrice * 100).toFixed(0)}¢</span>
        </div>
      </div>

      {phase === "error" && (
        <div className="rounded-2xl border border-red-500/40 bg-red-500/8 p-5 text-sm text-red-300">
          <p className="font-semibold mb-1">⚠ Could not reach the agent bridge</p>
          <p className="text-red-400/70 break-all text-xs mt-1">{errorMsg}</p>
          <p className="text-zinc-500 mt-3 text-xs">
            Run: <code className="font-mono text-zinc-400">uvicorn app.bridge_server:app --port 8080</code>
          </p>
        </div>
      )}

      <div className="flex flex-col gap-3">

        {/* Step 1 — Evidence Collection (single dispatched agent) */}
        <div className={`rounded-2xl border p-5 transition-all ${
          phase === "agents"
            ? "border-yellow-500/40 bg-yellow-500/5 pulse-glow"
            : "border-teal-500/30 bg-teal-500/5"
        }`}>
          <div className="flex items-center gap-2 mb-4">
            <span className="text-base">🔎</span>
            <span className="text-white font-semibold text-sm">Evidence Collection</span>
            {phase === "agents" && (
              <span className="ml-auto flex items-center gap-1.5 text-xs text-yellow-400">
                <Spinner /> Dispatching agent...
              </span>
            )}
            {phase !== "agents" && phase !== "error" && (
              <span className="ml-auto text-xs text-teal-400 font-medium">✓ Complete</span>
            )}
          </div>

          {/* Single agent card */}
          <div className={`rounded-xl border p-4 transition-all flex items-center gap-4 ${
            phase === "agents"
              ? "border-yellow-500/30 bg-yellow-500/5"
              : "border-teal-500/30 bg-teal-500/8"
          }`}>
            <span className="text-2xl">{agent.icon}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-zinc-200 font-medium">{agent.label}</p>
              {phase === "agents" && (
                <div className="mt-1.5 h-1 rounded-full shimmer w-32" />
              )}
              {phase !== "agents" && (
                <p className="text-xs text-zinc-500 mt-0.5">
                  {agent.chunks} chunks · {agent.rawTokens.toLocaleString()} tokens
                </p>
              )}
            </div>
            <div className="shrink-0">
              {phase === "agents" && <Spinner />}
              {phase !== "agents" && phase !== "error" && (
                <span className="text-teal-400 text-sm font-bold">✓</span>
              )}
            </div>
          </div>

          {/* Routing note */}
          <p className="text-xs text-zinc-600 mt-3">
            Orchestrator routed to <span className="text-zinc-400">{agent.label}</span> — single-agent dispatch
          </p>
        </div>

        {/* Step 2 — Compression */}
        <div className={`rounded-2xl border p-5 transition-all ${
          !["compressing", "deciding", "done"].includes(phase)
            ? "border-zinc-800 bg-zinc-900/40 opacity-40"
            : phase === "compressing"
            ? "border-yellow-500/40 bg-yellow-500/5 pulse-glow"
            : "border-teal-500/30 bg-teal-500/5"
        }`}>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-base">🗜️</span>
            <span className="text-white font-semibold text-sm">Context Compression</span>
            {phase === "compressing" && (
              <span className="ml-auto flex items-center gap-1.5 text-xs text-yellow-400">
                <Spinner /> Compressing...
              </span>
            )}
            {["deciding", "done"].includes(phase) && (
              <span className="ml-auto text-xs text-teal-400 font-medium">✓ Complete</span>
            )}
          </div>
          {["deciding", "done"].includes(phase) && rawTotal > 0 && compressedTokens > 0 && (
            <div className="flex items-center gap-4 mt-2">
              <div>
                <p className="text-xl font-bold text-zinc-300">{rawTotal.toLocaleString()}</p>
                <p className="text-xs text-zinc-500 mt-0.5">raw tokens</p>
              </div>
              <div className="flex-1 flex items-center gap-2">
                <div className="h-px flex-1 bg-zinc-700" />
                <div className="bg-teal-500/20 border border-teal-500/30 rounded-full px-3 py-1 text-sm font-bold text-teal-300">
                  {compressionRatio}x
                </div>
                <div className="h-px flex-1 bg-teal-600/50" />
              </div>
              <div>
                <p className="text-xl font-bold text-teal-400">{compressedTokens.toLocaleString()}</p>
                <p className="text-xs text-zinc-500 mt-0.5">to decision agent</p>
              </div>
            </div>
          )}
          {phase === "compressing" && (
            <div className="mt-2 h-1.5 rounded-full shimmer" />
          )}
        </div>

        {/* Step 3 — Decision Agent */}
        <div className={`rounded-2xl border p-5 transition-all ${
          !["deciding", "done"].includes(phase)
            ? "border-zinc-800 bg-zinc-900/40 opacity-40"
            : phase === "deciding"
            ? "border-yellow-500/40 bg-yellow-500/5 pulse-glow"
            : "border-teal-500/30 bg-teal-500/5"
        }`}>
          <div className="flex items-center gap-2">
            <span className="text-base">🤖</span>
            <span className="text-white font-semibold text-sm">Decision Agent</span>
            {phase === "deciding" && (
              <span className="ml-auto flex items-center gap-1.5 text-xs text-yellow-400">
                <Spinner /> Reasoning...
              </span>
            )}
            {phase === "done" && (
              <span className="ml-auto text-xs text-teal-400 font-medium">✓ Decision ready</span>
            )}
          </div>
          {phase === "deciding" && (
            <div className="mt-3 h-1.5 rounded-full shimmer" />
          )}
        </div>

      </div>
    </div>
  );
}
