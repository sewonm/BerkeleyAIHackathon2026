"use client";
import { AnalysisResult } from "@/lib/mockData";
import { BridgeAgent, ExecutionResult } from "@/lib/api";

interface Props {
  result: AnalysisResult;
  agents?: BridgeAgent[];
  execution?: ExecutionResult;
  question: string;
  ticker: string;
  onReset: () => void;
}

const REC_STYLES = {
  YES:  { bar: "bg-teal-500",  badge: "bg-teal-500 text-black",   glow: "shadow-teal-500/20" },
  NO:   { bar: "bg-red-500",   badge: "bg-red-500 text-white",    glow: "shadow-red-500/20"  },
  HOLD: { bar: "bg-yellow-400",badge: "bg-yellow-400 text-black", glow: "shadow-yellow-400/20"},
};

const RISK_CHECKS = [
  { label: "Confidence ≥ 70%",       key: "confidence" as const },
  { label: "Edge ≥ 5%",              key: "edge"       as const },
  { label: "Order size ≤ $5",        key: "orderSize"  as const },
  { label: "Market eligible",        key: "market"     as const },
];

function StatCard({ label, value, sub, accent = false }: { label: string; value: string; sub?: string; accent?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <p className="text-zinc-500 text-xs">{label}</p>
      <p className={`text-2xl font-bold ${accent ? "text-teal-400" : "text-white"}`}>{value}</p>
      {sub && <p className="text-zinc-600 text-xs">{sub}</p>}
    </div>
  );
}

export default function ResultsView({ result, agents = [], execution, question, ticker, onReset }: Props) {
  const rec = result.recommendation;
  const styles = REC_STYLES[rec];
  const totalChunks = agents.reduce((n, a) => n + a.chunks, 0);
  const usedAgents = agents.filter((a) => a.status === "done");

  const riskChecks = [
    result.confidence >= 0.7,
    Math.abs(result.edge) >= 0.05,
    result.orderSize <= 5,
    true,
  ];

  return (
    <div className="flex flex-col gap-5 fade-in-up">

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-teal-500 text-xs font-mono mb-1">{ticker}</p>
          <h2 className="text-white text-xl font-semibold leading-snug">{question}</h2>
        </div>
        <button
          onClick={onReset}
          className="shrink-0 text-zinc-500 hover:text-white text-xs border border-zinc-700 hover:border-zinc-500 px-3 py-1.5 rounded-lg transition"
        >
          ← New market
        </button>
      </div>

      {/* Decision banner */}
      <div className={`rounded-2xl border border-zinc-700 bg-zinc-900 p-6 shadow-xl ${styles.glow}`}>
        <div className="flex flex-col sm:flex-row gap-6 items-center">
          {/* Recommendation */}
          <div className={`text-4xl font-black px-8 py-4 rounded-xl ${styles.badge} shrink-0 shadow-lg`}>
            {rec}
          </div>

          {/* Confidence bar */}
          <div className="flex-1 w-full">
            <div className="flex justify-between items-baseline mb-2">
              <span className="text-zinc-400 text-xs font-medium uppercase tracking-wider">Confidence</span>
              <span className="text-white font-bold">{(result.confidence * 100).toFixed(0)}%</span>
            </div>
            <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${styles.bar}`}
                style={{ width: `${result.confidence * 100}%` }}
              />
            </div>
          </div>

          {/* Fair prob */}
          <div className="text-center shrink-0">
            <p className="text-zinc-500 text-xs mb-1">Fair value</p>
            <p className="text-white text-3xl font-bold">{(result.fairProbability * 100).toFixed(0)}¢</p>
            <p className="text-zinc-600 text-xs mt-0.5">market {(result.yesPrice * 100).toFixed(0)}¢</p>
          </div>

          {/* Edge */}
          <div className="text-center shrink-0">
            <p className="text-zinc-500 text-xs mb-1">Edge</p>
            <p className={`text-3xl font-bold ${result.edge >= 0 ? "text-teal-400" : "text-red-400"}`}>
              {result.edge >= 0 ? "+" : ""}{(result.edge * 100).toFixed(0)}¢
            </p>
          </div>
        </div>
      </div>

      {/* Compression + agent row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

        {/* Compression */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5">
          <p className="text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-4">🗜️ Compression Pipeline</p>
          <div className="flex items-center gap-3">
            <StatCard label="Raw tokens" value={result.rawTokens.toLocaleString()} />
            <div className="flex-1 flex flex-col items-center gap-1">
              <div className="bg-teal-500/15 border border-teal-500/25 rounded-full px-3 py-1 text-sm font-bold text-teal-300">
                {result.compressionRatio}x
              </div>
              <div className="flex items-center gap-1 w-full">
                <div className="h-px flex-1 bg-zinc-700" />
                <div className="h-px flex-1 bg-teal-600/50" />
              </div>
            </div>
            <StatCard label="Compressed" value={result.compressedTokens.toLocaleString()} accent />
          </div>
          <p className="text-zinc-600 text-xs mt-3">
            {(result.rawTokens - result.compressedTokens).toLocaleString()} tokens saved · {(((result.rawTokens - result.compressedTokens) / result.rawTokens) * 100).toFixed(0)}% reduction
          </p>
        </div>

        {/* Agents */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-zinc-400 text-xs font-semibold uppercase tracking-wider">🔗 Agents</p>
            <span className="text-xs text-zinc-600">{usedAgents.length} active · {totalChunks} chunks</span>
          </div>
          <div className="flex flex-col gap-2.5">
            {agents.map((a) => (
              <div key={a.id} className="flex items-center gap-3">
                <span className="text-base w-6 text-center">{a.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-zinc-300 truncate">{a.label}</p>
                </div>
                <span className={`text-xs font-mono px-2 py-0.5 rounded-full shrink-0 ${
                  a.status === "done" ? "bg-teal-500/15 text-teal-400" : "bg-zinc-800 text-zinc-600"
                }`}>
                  {a.status === "done" ? `${a.chunks} chunks` : "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Evidence + reasoning */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5">
          <p className="text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-3">📌 Key Evidence</p>
          <ul className="flex flex-col gap-2.5">
            {result.keyEvidence.map((e, i) => (
              <li key={i} className="flex gap-2 text-sm text-zinc-300 leading-snug">
                <span className="text-teal-500 shrink-0 mt-0.5">·</span>
                {e}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5">
          <p className="text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-3">💬 Reasoning</p>
          <p className="text-sm text-zinc-400 leading-relaxed">{result.reasoning}</p>
          {result.missingInfo.length > 0 && (
            <div className="mt-4 pt-4 border-t border-zinc-800">
              <p className="text-zinc-600 text-xs font-semibold uppercase tracking-wider mb-2">Gaps</p>
              <ul className="flex flex-col gap-1.5">
                {result.missingInfo.map((m, i) => (
                  <li key={i} className="text-xs text-zinc-600 flex gap-2">
                    <span className="shrink-0">⚠</span>{m}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Risk manager + trade executor */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

        {/* Risk */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5">
          <p className="text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-4">🛡️ Risk Manager</p>
          <ul className="flex flex-col gap-2.5">
            {RISK_CHECKS.map((check, i) => (
              <li key={i} className="flex items-center gap-2.5 text-sm">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs shrink-0 ${
                  riskChecks[i] ? "bg-teal-500/20 text-teal-400" : "bg-red-500/20 text-red-400"
                }`}>
                  {riskChecks[i] ? "✓" : "✗"}
                </span>
                <span className={riskChecks[i] ? "text-zinc-300" : "text-zinc-600"}>
                  {check.label}
                </span>
              </li>
            ))}
          </ul>
          <div className={`mt-4 px-3 py-2.5 rounded-xl text-sm font-semibold ${
            result.riskApproved
              ? "bg-teal-500/10 text-teal-300 border border-teal-500/20"
              : "bg-red-500/10 text-red-400 border border-red-500/20"
          }`}>
            {result.riskApproved ? "✓ Approved for execution" : `✗ ${result.riskRejectReason ?? "Rejected"}`}
          </div>
        </div>

        {/* Trade executor */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5">
          <p className="text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-4">⚡ Trade Executor</p>
          <div className="flex flex-col gap-3 text-sm">
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Mode</span>
              <span className={`font-mono text-xs px-2 py-0.5 rounded-full border ${
                result.tradeMode === "demo"
                  ? "border-teal-500/30 bg-teal-500/10 text-teal-300"
                  : "border-zinc-700 bg-zinc-800 text-zinc-400"
              }`}>{result.tradeMode}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Action</span>
              <span className="font-mono text-zinc-200 text-xs">{execution?.action ?? result.tradeAction}</span>
            </div>
            {execution?.estimatedContracts != null && (
              <div className="flex justify-between items-center">
                <span className="text-zinc-500">Contracts</span>
                <span className="font-mono text-zinc-200">{execution.estimatedContracts}</span>
              </div>
            )}
            {execution?.estimatedCostDollars != null && (
              <div className="flex justify-between items-center">
                <span className="text-zinc-500">Cost</span>
                <span className="font-mono text-zinc-200">${execution.estimatedCostDollars.toFixed(2)}</span>
              </div>
            )}
          </div>

          <div className={`mt-4 px-3 py-2.5 rounded-xl text-sm font-semibold ${
            execution?.approved
              ? "bg-teal-500/10 text-teal-300 border border-teal-500/20"
              : "bg-zinc-800 text-zinc-500 border border-zinc-700"
          }`}>
            {execution?.approved ? "✓ Order simulated (demo mode)" : `✗ ${execution?.reason ?? "No order placed"}`}
          </div>

          {execution?.kalshiResponse && (
            <details className="mt-3">
              <summary className="text-xs text-zinc-600 cursor-pointer hover:text-zinc-400 transition select-none">
                View order payload ↓
              </summary>
              <pre className="mt-2 text-xs text-zinc-500 bg-zinc-950 rounded-xl p-3 overflow-x-auto border border-zinc-800">
                {JSON.stringify(execution.kalshiResponse, null, 2)}
              </pre>
            </details>
          )}
        </div>
      </div>

      {/* Source evidence from agents */}
      {usedAgents.some((a) => a.sources && a.sources.length > 0) && (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5">
          <p className="text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-4">🌐 Live Sources</p>
          <div className="flex flex-col gap-4">
            {agents.filter((a) => a.sources && a.sources.length > 0).map((a) => (
              <div key={a.id} className="border-l-2 border-zinc-700 pl-4">
                <div className="flex items-center gap-2 mb-2">
                  <span>{a.icon}</span>
                  <span className="text-xs text-zinc-400 font-medium">{a.label}</span>
                </div>
                <ul className="flex flex-col gap-2">
                  {a.sources!.map((s, i) => (
                    <li key={i} className="text-xs">
                      {s.url ? (
                        <a href={s.url} target="_blank" rel="noopener noreferrer"
                          className="text-teal-500 hover:text-teal-300 truncate block max-w-sm transition">
                          {s.url}
                        </a>
                      ) : (
                        <span className="text-zinc-600">{s.kind || "evidence"}</span>
                      )}
                      {s.snippet && (
                        <p className="text-zinc-600 mt-0.5 leading-snug">{s.snippet}</p>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
