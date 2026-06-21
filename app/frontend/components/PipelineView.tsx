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

const AGENT_META: Record<string, { label: string; icon: string; desc: string }> = {
  financial: { label: "Financial Research Agent", icon: "📈", desc: "Fetching Kalshi market data, orderbook depth, price history" },
  culture:   { label: "Culture Web Agent",        icon: "🌐", desc: "Searching live web sources, news, and cultural signals" },
  sports:    { label: "Sports Video Agent",       icon: "⚽", desc: "Pulling ESPN stats, injury reports, odds, and team data" },
};

type Phase = "routing" | "agents" | "compressing" | "deciding" | "executing" | "done" | "error";

const PHASE_MESSAGES: Record<Phase, string[]> = {
  routing:     ["Orchestrator analyzing market question...", "Running LLM routing classification...", "Selecting optimal evidence agent..."],
  agents:      ["Dispatching to evidence agent via Fetch.ai...", "Collecting live market intelligence...", "Processing evidence chunks..."],
  compressing: ["Running context compression pipeline...", "Scoring chunks by relevance and novelty...", "Deduplicating and token-budgeting..."],
  deciding:    ["Sending compressed context to Claude...", "Analyzing evidence against market price...", "Generating trading recommendation..."],
  executing:   ["Running risk manager checks...", "Validating confidence and edge thresholds...", "Building Kalshi order payload..."],
  done:        ["Analysis complete."],
  error:       ["Pipeline error."],
};

function Spinner({ size = "sm" }: { size?: "sm" | "md" }) {
  const s = size === "md" ? "w-5 h-5" : "w-3.5 h-3.5";
  return (
    <svg className={`animate-spin ${s} text-teal-400`} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" strokeOpacity="0.15"/>
      <path d="M12 2a10 10 0 0110 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="w-3.5 h-3.5 text-teal-400" viewBox="0 0 14 14" fill="none">
      <path d="M2.5 7L5.5 10L11.5 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

export default function PipelineView({ question, ticker, yesPrice, category, onComplete }: Props) {
  const [dispatchedAgent, setDispatchedAgent] = useState<BridgeAgent | null>(null);
  const [phase, setPhase] = useState<Phase>("routing");
  const [msgIndex, setMsgIndex] = useState(0);
  const [rawTotal, setRawTotal] = useState(0);
  const [compressedTokens, setCompressedTokens] = useState(0);
  const [compressionRatio, setCompressionRatio] = useState(0);
  const [cacheHit, setCacheHit] = useState<boolean | null>(null);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const startedRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pendingCategory = (() => {
    if (category && !["auto", "custom", ""].includes(category)) return category;
    const q = question.toLowerCase();
    if (/nba|nfl|mlb|nhl|soccer|football|basketball|baseball|hockey|world cup|playoff|lakers|yankees|lebron|sport|game|match|player|team|championship|win the|beat/.test(q)) return "sports";
    if (/bitcoin|btc|eth|crypto|fed|rate|interest|inflation|stock|s&p|nasdaq|gdp|earnings|cpi/.test(q)) return "financial";
    return "culture";
  })();

  const agentMeta = AGENT_META[pendingCategory] ?? AGENT_META["culture"];
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const resolvedAgent = dispatchedAgent ?? { id: pendingCategory, label: agentMeta.label, icon: agentMeta.icon, status: "processing" as const, chunks: 0, rawTokens: 0 };

  // Rotate status messages within each phase
  useEffect(() => {
    const msgs = PHASE_MESSAGES[phase] ?? [];
    setMsgIndex(0);
    if (msgs.length <= 1) return;
    const t = setInterval(() => setMsgIndex(i => (i + 1) % msgs.length), 2200);
    return () => clearInterval(t);
  }, [phase]);

  // Elapsed timer
  useEffect(() => {
    timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    (async () => {
      try {
        setTimeout(() => setPhase("agents"), 1200);
        const data = await analyzeMarket({ question, ticker, yesPrice, category });
        const ag = data.agents[0] ?? null;
        setDispatchedAgent(ag);
        setRawTotal(data.rawTokens);
        setCacheHit(data.cacheHit ?? false);
        setElapsedMs(data.elapsedSeconds != null ? Math.round(data.elapsedSeconds * 1000) : null);
        setPhase("compressing");
        setTimeout(() => {
          setCompressedTokens(data.compressedTokens);
          setCompressionRatio(data.compressionRatio);
          setPhase("deciding");
          setTimeout(() => {
            setPhase("executing");
            setTimeout(() => {
              setPhase("done");
              if (timerRef.current) clearInterval(timerRef.current);
              onComplete(data);
            }, 900);
          }, 1200);
        }, 800);
      } catch (e) {
        setErrorMsg(e instanceof Error ? e.message : String(e));
        setPhase("error");
        if (timerRef.current) clearInterval(timerRef.current);
      }
    })();
  }, []);

  const PHASE_ORDER: Phase[] = ["routing", "agents", "compressing", "deciding", "executing"];
  const currentIndex = PHASE_ORDER.indexOf(phase);

  const steps = [
    { id: "routing",     label: "LLM Routing",          sub: `→ ${agentMeta.label}` },
    { id: "agents",      label: "Evidence Collection",  sub: phase === "agents" ? agentMeta.desc : dispatchedAgent ? `${dispatchedAgent.chunks} chunks · ${dispatchedAgent.rawTokens.toLocaleString()} tokens` : agentMeta.desc },
    { id: "compressing", label: "Context Compression",  sub: rawTotal > 0 && compressedTokens > 0 ? `${rawTotal.toLocaleString()} → ${compressedTokens.toLocaleString()} tokens (${compressionRatio}x)` : "Scoring and deduplicating evidence chunks" },
    { id: "deciding",    label: "Claude Decision Agent", sub: "Analyzing compressed context against market price" },
    { id: "executing",   label: "Risk Manager & Executor", sub: "Validating trade and building Kalshi order" },
  ];

  if (phase === "error") {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 fade-in">
        <div className="max-w-lg w-full rounded-2xl border border-red-500/30 bg-red-500/5 p-8 text-center">
          <p className="text-red-400 font-semibold mb-2">Pipeline Error</p>
          <p className="text-red-400/60 text-sm break-all">{errorMsg}</p>
          <p className="text-zinc-600 text-xs mt-4">Make sure the bridge is running on port 8080</p>
        </div>
      </div>
    );
  }

  const currentMsg = (PHASE_MESSAGES[phase] ?? [""])[msgIndex];

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 fade-in">
      <div className="w-full max-w-xl">

        {/* Market question */}
        <div className="mb-10 text-center">
          {ticker && <p className="text-teal-600 text-xs font-mono mb-2 tracking-wider">{ticker}</p>}
          <h2 className="text-zinc-200 text-xl font-semibold leading-snug max-w-md mx-auto">{question}</h2>
          {yesPrice > 0 && (
            <p className="text-zinc-600 text-sm mt-2">Market price: <span className="text-zinc-400 font-mono">{(yesPrice * 100).toFixed(0)}¢</span></p>
          )}
        </div>

        {/* Status message */}
        <div className="flex items-center justify-center gap-2 mb-8 h-6">
          {phase !== "done" && <Spinner size="md" />}
          <p className="text-zinc-400 text-sm font-medium transition-all duration-300">{currentMsg}</p>
        </div>

        {/* Pipeline steps */}
        <div className="flex flex-col gap-0">
          {steps.map((step, i) => {
            const stepIndex = PHASE_ORDER.indexOf(step.id as Phase);
            const isDone = stepIndex < currentIndex;
            const isActive = stepIndex === currentIndex;
            const isPending = stepIndex > currentIndex;

            return (
              <div key={step.id} className="flex gap-4">
                {/* Timeline */}
                <div className="flex flex-col items-center">
                  <div className={`w-7 h-7 rounded-full border flex items-center justify-center shrink-0 transition-all duration-500 ${
                    isDone   ? "border-teal-500/40 bg-teal-500/10" :
                    isActive ? "border-teal-400/60 bg-teal-400/8 shadow-[0_0_12px_rgba(20,184,166,0.15)]" :
                               "border-zinc-800 bg-zinc-900/50"
                  }`}>
                    {isDone   ? <CheckIcon /> :
                     isActive ? <Spinner size="sm" /> :
                                <span className="w-1.5 h-1.5 rounded-full bg-zinc-700" />}
                  </div>
                  {i < steps.length - 1 && (
                    <div className={`w-px flex-1 my-1 transition-all duration-700 ${isDone ? "bg-teal-600/30" : "bg-zinc-800"}`} style={{ minHeight: "28px" }} />
                  )}
                </div>

                {/* Content */}
                <div className={`pb-6 flex-1 transition-all duration-300 ${isPending ? "opacity-30" : ""}`}>
                  <div className="flex items-baseline gap-2 mb-0.5">
                    <p className={`text-sm font-medium ${isActive ? "text-white" : isDone ? "text-zinc-400" : "text-zinc-600"}`}>
                      {step.label}
                    </p>
                    {isActive && (
                      <span className="text-xs text-teal-500 blink">●</span>
                    )}
                  </div>
                  <p className={`text-xs leading-relaxed ${isActive ? "text-zinc-400" : isDone ? "text-zinc-600" : "text-zinc-700"}`}>
                    {step.sub}
                  </p>
                  {step.id === "compressing" && isDone && cacheHit !== null && (
                    <div className="mt-1.5 flex items-center gap-1.5">
                      {cacheHit === true ? (
                        <span className="flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-yellow-400/15 border border-yellow-400/30 text-yellow-300">
                          ⚡ Redis HIT{elapsedMs != null ? ` · ${elapsedMs}ms` : ""}
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-zinc-800 border border-zinc-700 text-zinc-500">
                          💾 Cached{elapsedMs != null ? ` · ${(elapsedMs / 1000).toFixed(1)}s` : ""}
                        </span>
                      )}
                    </div>
                  )}
                  {isActive && (
                    <div className="mt-2 h-px bg-zinc-800 rounded overflow-hidden">
                      <div className="h-full bg-teal-500/40 rounded shimmer" style={{ width: "60%" }} />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Elapsed */}
        <div className="mt-4 text-center">
          <span className="text-zinc-700 text-xs font-mono">{elapsed}s elapsed</span>
        </div>
      </div>
    </div>
  );
}
