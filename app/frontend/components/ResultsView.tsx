"use client";
import { useState } from "react";
import { AnalysisResult } from "@/lib/mockData";
import { BridgeAgent, ExecutionResult } from "@/lib/api";

interface Props {
  result: AnalysisResult;
  agents?: BridgeAgent[];
  execution?: ExecutionResult;
  question: string;
  ticker: string;
  cacheHit?: boolean;
  elapsedSeconds?: number;
  onReset: () => void;
}

const REC_STYLES = {
  YES:  { badge: "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30", bar: "bg-emerald-500", dot: "bg-emerald-400" },
  NO:   { badge: "bg-red-500/15 text-red-300 border border-red-500/30",             bar: "bg-red-500",     dot: "bg-red-400"     },
  HOLD: { badge: "bg-amber-500/15 text-amber-300 border border-amber-500/30",       bar: "bg-amber-400",   dot: "bg-amber-400"   },
};

const RISK_CHECKS = [
  { label: "Confidence ≥ 70%",  key: "confidence" as const },
  { label: "Edge ≥ 3%",         key: "edge"       as const },
  { label: "Order size ≤ $5",   key: "orderSize"  as const },
  { label: "Market eligible",   key: "market"     as const },
];

function Section({ title, defaultOpen = true, children }: { title: string; defaultOpen?: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/60 overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-zinc-800/30 transition"
      >
        <span className="text-zinc-300 text-xs font-semibold uppercase tracking-widest">{title}</span>
        <svg className={`w-3.5 h-3.5 text-zinc-600 transition-transform duration-200 ${open ? "rotate-180" : ""}`} viewBox="0 0 14 14" fill="none">
          <path d="M3 5l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
      {open && <div className="px-5 pb-5 pt-1 border-t border-zinc-800/60">{children}</div>}
    </div>
  );
}

export default function ResultsView({ result, agents = [], execution, question, ticker, cacheHit, elapsedSeconds, onReset }: Props) {
  const rec = result.recommendation;
  const styles = REC_STYLES[rec];
  const totalChunks = agents.reduce((n, a) => n + a.chunks, 0);
  const usedAgents = agents.filter((a) => a.status === "done");

  const riskChecks = [
    result.confidence >= 0.7,
    Math.abs(result.edge) >= 0.03,
    result.orderSize <= 5,
    true,
  ];
  const allPassed = riskChecks.every(Boolean);

  return (
    <div className="flex flex-col gap-4 fade-in-up max-w-3xl mx-auto">

      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-2">
        <div className="min-w-0">
          {ticker && <p className="text-zinc-600 text-xs font-mono mb-1">{ticker}</p>}
          <h2 className="text-zinc-100 text-xl font-semibold leading-snug">{question}</h2>
        </div>
        <button
          onClick={onReset}
          className="shrink-0 text-zinc-600 hover:text-zinc-300 text-xs border border-zinc-800 hover:border-zinc-700 px-3 py-1.5 rounded-lg transition"
        >
          ← New
        </button>
      </div>

      {/* Decision banner */}
      <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/60 p-5">
        <div className="flex flex-col sm:flex-row gap-5 items-start sm:items-center">
          {/* Badge */}
          <div className={`text-2xl font-black px-5 py-2.5 rounded-lg tracking-wide shrink-0 ${styles.badge}`}>
            {rec}
          </div>

          {/* Confidence */}
          <div className="flex-1 w-full">
            <div className="flex justify-between items-baseline mb-1.5">
              <span className="text-zinc-500 text-xs uppercase tracking-wider">Confidence</span>
              <span className="text-zinc-200 font-semibold text-sm">{(result.confidence * 100).toFixed(0)}%</span>
            </div>
            <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${styles.bar} transition-all duration-700`} style={{ width: `${result.confidence * 100}%` }} />
            </div>
          </div>

          {/* Stats */}
          <div className="flex gap-6 shrink-0">
            <div className="text-center">
              <p className="text-zinc-500 text-xs mb-0.5">Fair value</p>
              <p className="text-zinc-100 text-xl font-bold font-mono">{(result.fairProbability * 100).toFixed(0)}¢</p>
              <p className="text-zinc-500 text-xs">market {(result.yesPrice * 100).toFixed(0)}¢</p>
            </div>
            <div className="text-center">
              <p className="text-zinc-500 text-xs mb-0.5">Edge</p>
              <p className={`text-xl font-bold font-mono ${result.edge >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {result.edge >= 0 ? "+" : ""}{(result.edge * 100).toFixed(0)}¢
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Compression */}
      <Section title="Compression Pipeline">
        {(cacheHit === true || cacheHit === false) && (
          <div className="flex items-center gap-2 mt-2 mb-3">
            {cacheHit === true ? (
              <span className="flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-yellow-400/15 border border-yellow-400/30 text-yellow-300">
                ⚡ Redis HIT{elapsedSeconds != null ? ` · ${Math.round(elapsedSeconds * 1000)}ms` : ""}
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-zinc-800 border border-zinc-700 text-zinc-500">
                💾 Cached to Redis{elapsedSeconds != null ? ` · ${elapsedSeconds.toFixed(2)}s` : ""}
              </span>
            )}
          </div>
        )}
        <div className="flex items-center gap-4 py-2">
          <div>
            <p className="text-lg font-bold font-mono text-zinc-300">{result.rawTokens.toLocaleString()}</p>
            <p className="text-xs text-zinc-500 mt-0.5">raw tokens</p>
          </div>
          <div className="flex-1 flex items-center gap-2">
            <div className="h-px flex-1 bg-zinc-800" />
            <span className="text-xs font-bold text-teal-400 border border-teal-500/30 bg-teal-500/10 px-2.5 py-1 rounded-full font-mono">
              {result.compressionRatio}×
            </span>
            <div className="h-px flex-1 bg-teal-700/40" />
          </div>
          <div className="text-right">
            <p className="text-lg font-bold font-mono text-teal-400">{result.compressedTokens.toLocaleString()}</p>
            <p className="text-xs text-zinc-500 mt-0.5">to Claude</p>
          </div>
        </div>
        <p className="text-zinc-500 text-xs mt-1">
          {(result.rawTokens - result.compressedTokens).toLocaleString()} tokens removed · {(((result.rawTokens - result.compressedTokens) / result.rawTokens) * 100).toFixed(0)}% reduction
        </p>
      </Section>

      {/* Agents */}
      {usedAgents.length > 0 && (
        <Section title="Agents Utilized">
          <div className="flex flex-col gap-3 mt-1">
            {agents.map((a) => (
              <div key={a.id} className="flex items-center gap-3">
                <span className="text-base w-6 text-center">{a.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-zinc-300">{a.label}</p>
                  {a.sources && a.sources.length > 0 && (
                    <div className="flex flex-col gap-1 mt-1">
                      {a.sources.slice(0, 3).map((s, i) => s.url && (
                        <a key={i} href={s.url} target="_blank" rel="noopener noreferrer"
                          className="text-xs text-zinc-600 hover:text-teal-500 truncate block max-w-sm transition">
                          {s.url}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
                <span className="text-xs font-mono text-zinc-500 shrink-0">
                  {a.status === "done" ? `${a.chunks} chunks` : "—"}
                </span>
              </div>
            ))}
            <p className="text-zinc-500 text-xs mt-1 border-t border-zinc-800/60 pt-3">
              {usedAgents.length} agent dispatched via Fetch.ai uAgents · {totalChunks} evidence chunks collected
            </p>
          </div>
        </Section>
      )}

      {/* Key Evidence */}
      <Section title="Key Evidence">
        <ul className="flex flex-col gap-2.5 mt-1">
          {result.keyEvidence.map((e, i) => (
            <li key={i} className="flex gap-3 text-sm text-zinc-400 leading-relaxed">
              <span className="text-teal-600 shrink-0 font-mono text-xs mt-0.5">{String(i + 1).padStart(2, "0")}</span>
              {e}
            </li>
          ))}
        </ul>
      </Section>

      {/* Reasoning */}
      <Section title="Claude Reasoning">
        <p className="text-sm text-zinc-400 leading-relaxed mt-1">{result.reasoning}</p>
        {result.missingInfo.length > 0 && (
          <div className="mt-4 pt-4 border-t border-zinc-800/60">
            <p className="text-zinc-500 text-xs uppercase tracking-widest mb-2">Information gaps</p>
            <ul className="flex flex-col gap-1.5">
              {result.missingInfo.map((m, i) => (
                <li key={i} className="text-xs text-zinc-500 flex gap-2">
                  <span className="shrink-0">—</span>{m}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Section>

      {/* Risk + Execution side by side */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

        <Section title="Risk Manager">
          <ul className="flex flex-col gap-2.5 mt-1">
            {RISK_CHECKS.map((check, i) => (
              <li key={i} className="flex items-center gap-2.5">
                <span className={`w-4 h-4 rounded flex items-center justify-center text-xs shrink-0 ${
                  riskChecks[i] ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"
                }`}>
                  {riskChecks[i] ? "✓" : "✗"}
                </span>
                <span className={`text-xs ${riskChecks[i] ? "text-zinc-400" : "text-zinc-600"}`}>{check.label}</span>
              </li>
            ))}
          </ul>
          <div className={`mt-4 px-3 py-2 rounded-lg text-xs font-medium ${
            allPassed ? "bg-emerald-500/8 text-emerald-400 border border-emerald-500/20" : "bg-red-500/8 text-red-400 border border-red-500/20"
          }`}>
            {allPassed ? "✓ Approved for execution" : `✗ ${result.riskRejectReason ?? "Rejected"}`}
          </div>
        </Section>

        <Section title="Trade Executor">
          <div className="flex flex-col gap-2.5 mt-1 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Mode</span>
              <span className={`font-mono px-2 py-0.5 rounded-full border ${
                result.tradeMode === "demo"
                  ? "border-teal-500/25 bg-teal-500/8 text-teal-400"
                  : "border-zinc-800 bg-zinc-900 text-zinc-500"
              }`}>{result.tradeMode}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Action</span>
              <span className="font-mono text-zinc-300">{execution?.action ?? "—"}</span>
            </div>
            {execution?.estimatedContracts != null && (
              <div className="flex justify-between items-center">
                <span className="text-zinc-500">Contracts</span>
                <span className="font-mono text-zinc-300">{execution.estimatedContracts}</span>
              </div>
            )}
            {execution?.estimatedCostDollars != null && (
              <div className="flex justify-between items-center">
                <span className="text-zinc-500">Cost</span>
                <span className="font-mono text-zinc-300">${execution.estimatedCostDollars.toFixed(2)}</span>
              </div>
            )}
          </div>
          <div className={`mt-4 px-3 py-2 rounded-lg text-xs font-medium ${
            execution?.approved
              ? "bg-teal-500/8 text-teal-400 border border-teal-500/20"
              : "bg-zinc-800/60 text-zinc-500 border border-zinc-800"
          }`}>
            {execution?.approved ? "✓ Order simulated (demo)" : `✗ ${execution?.reason ?? "No order placed"}`}
          </div>
          {!!execution?.kalshiResponse && (
            <details className="mt-3">
              <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-300 transition select-none">
                View order payload
              </summary>
              <pre className="mt-2 text-xs text-zinc-600 bg-zinc-950 rounded-lg p-3 overflow-x-auto border border-zinc-800/60 font-mono leading-relaxed">
                {JSON.stringify(execution.kalshiResponse as object, null, 2)}
              </pre>
            </details>
          )}
        </Section>
      </div>

    </div>
  );
}
