"use client";
import { AnalysisResult } from "@/lib/mockData";
import { BridgeAgent } from "@/lib/api";

interface Props {
  result: AnalysisResult;
  agents?: BridgeAgent[];
  question: string;
  ticker: string;
  onReset: () => void;
}

const REC_COLORS = {
  YES: "bg-green-500 text-black",
  NO: "bg-red-500 text-white",
  HOLD: "bg-yellow-400 text-black",
};

const RISK_CHECKS = [
  { label: "Confidence threshold (≥70%)", key: "confidence" as const },
  { label: "Minimum edge (≥5%)", key: "edge" as const },
  { label: "Order size within limit ($5 max)", key: "orderSize" as const },
  { label: "Market allowed", key: "market" as const },
];

export default function ResultsView({ result, agents = [], question, ticker, onReset }: Props) {
  const totalChunks = agents.reduce((n, a) => n + a.chunks, 0);
  const usedAgents = agents.filter((a) => a.status === "done");
  const riskChecks = [
    result.confidence >= 0.7,
    Math.abs(result.edge) >= 0.05,
    result.orderSize <= 5,
    true,
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-zinc-500 text-xs font-mono mb-1">{ticker}</p>
          <h2 className="text-white text-lg font-semibold max-w-lg">{question}</h2>
        </div>
        <button
          onClick={onReset}
          className="text-zinc-400 hover:text-white text-sm border border-zinc-700 px-3 py-1.5 rounded-lg transition shrink-0"
        >
          ← New market
        </button>
      </div>

      {/* Decision banner */}
      <div className="rounded-xl border border-zinc-700 bg-zinc-800 p-5 flex flex-col sm:flex-row gap-4 items-center">
        <div className={`text-3xl font-black px-6 py-3 rounded-xl ${REC_COLORS[result.recommendation]}`}>
          {result.recommendation}
        </div>
        <div className="flex-1">
          <p className="text-zinc-400 text-sm">Confidence</p>
          <div className="flex items-center gap-3 mt-1">
            <div className="flex-1 h-2 bg-zinc-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-teal-400 rounded-full"
                style={{ width: `${result.confidence * 100}%` }}
              />
            </div>
            <span className="text-white font-bold text-sm">{(result.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
        <div className="text-center">
          <p className="text-zinc-500 text-xs">Fair probability</p>
          <p className="text-white text-2xl font-bold">{(result.fairProbability * 100).toFixed(0)}¢</p>
          <p className="text-zinc-500 text-xs">vs market {(result.yesPrice * 100).toFixed(0)}¢</p>
        </div>
        <div className="text-center">
          <p className="text-zinc-500 text-xs">Edge</p>
          <p className={`text-2xl font-bold ${result.edge >= 0 ? "text-green-400" : "text-red-400"}`}>
            {result.edge >= 0 ? "+" : ""}{(result.edge * 100).toFixed(0)}¢
          </p>
        </div>
      </div>

      {/* Compression metrics */}
      <div className="rounded-xl border border-zinc-700 bg-zinc-800 p-5">
        <h3 className="text-zinc-300 font-semibold mb-4">🗜️ Compression Pipeline</h3>
        <div className="flex items-center gap-6">
          <div>
            <p className="text-3xl font-bold text-zinc-300">{result.rawTokens.toLocaleString()}</p>
            <p className="text-xs text-zinc-500">raw tokens in</p>
          </div>
          <div className="flex-1 flex items-center gap-2">
            <div className="h-px flex-1 bg-zinc-700" />
            <span className="text-teal-400 font-bold text-lg">{result.compressionRatio}x</span>
            <div className="h-px flex-1 bg-teal-500" />
          </div>
          <div>
            <p className="text-3xl font-bold text-teal-400">{result.compressedTokens.toLocaleString()}</p>
            <p className="text-xs text-zinc-500">tokens to Claude</p>
          </div>
        </div>
        <p className="text-zinc-500 text-xs mt-3">
          Saved {(result.rawTokens - result.compressedTokens).toLocaleString()} tokens ·{" "}
          {(((result.rawTokens - result.compressedTokens) / result.rawTokens) * 100).toFixed(0)}% reduction
        </p>
      </div>

      {/* Agents utilized — real per-agent evidence from the live collectors */}
      {agents.length > 0 && (
        <div className="rounded-xl border border-zinc-700 bg-zinc-800 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-zinc-300 font-semibold">🔗 Agents Utilized</h3>
            <span className="text-xs text-zinc-500">
              {usedAgents.length} agent{usedAgents.length === 1 ? "" : "s"} · {totalChunks} live evidence chunks
            </span>
          </div>
          <div className="flex flex-col gap-4">
            {agents.map((a) => (
              <div key={a.id} className="border-l-2 border-teal-600 pl-3">
                <div className="flex items-center gap-2 mb-1">
                  <span>{a.icon}</span>
                  <span className="text-sm text-zinc-200 font-medium">{a.label}</span>
                  <span
                    className={`text-xs font-mono px-2 py-0.5 rounded-full ${
                      a.status === "done"
                        ? "bg-teal-500/20 text-teal-300"
                        : "bg-zinc-700 text-zinc-500"
                    }`}
                  >
                    {a.status === "done" ? `${a.chunks} chunks · ${a.rawTokens.toLocaleString()} tok` : "no data"}
                  </span>
                </div>
                {a.sources && a.sources.length > 0 && (
                  <ul className="flex flex-col gap-1.5 mt-2">
                    {a.sources.map((s, i) => (
                      <li key={i} className="text-xs">
                        <div className="flex items-center gap-2">
                          {s.via && (
                            <span className="font-mono text-zinc-600">[{s.via}]</span>
                          )}
                          {s.url ? (
                            <a
                              href={s.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-teal-400 hover:text-teal-300 truncate max-w-md"
                            >
                              {s.url}
                            </a>
                          ) : (
                            <span className="text-zinc-500">{s.kind || "evidence"}</span>
                          )}
                        </div>
                        {s.snippet && (
                          <p className="text-zinc-500 mt-0.5 leading-snug">{s.snippet}</p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence + reasoning */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-xl border border-zinc-700 bg-zinc-800 p-5">
          <h3 className="text-zinc-300 font-semibold mb-3">📌 Key Evidence</h3>
          <ul className="flex flex-col gap-2">
            {result.keyEvidence.map((e, i) => (
              <li key={i} className="flex gap-2 text-sm text-zinc-300">
                <span className="text-teal-400 shrink-0">·</span>
                {e}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-zinc-700 bg-zinc-800 p-5">
          <h3 className="text-zinc-300 font-semibold mb-3">💬 Reasoning</h3>
          <p className="text-sm text-zinc-400 leading-relaxed">{result.reasoning}</p>
          {result.missingInfo.length > 0 && (
            <>
              <h4 className="text-zinc-500 text-xs font-semibold mt-4 mb-2 uppercase tracking-wide">Missing info</h4>
              <ul className="flex flex-col gap-1">
                {result.missingInfo.map((m, i) => (
                  <li key={i} className="text-xs text-zinc-500 flex gap-2">
                    <span>⚠</span>{m}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>

      {/* Risk manager + trade */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-xl border border-zinc-700 bg-zinc-800 p-5">
          <h3 className="text-zinc-300 font-semibold mb-3">🛡️ Risk Manager</h3>
          <ul className="flex flex-col gap-2">
            {RISK_CHECKS.map((check, i) => (
              <li key={i} className="flex items-center gap-2 text-sm">
                <span className={riskChecks[i] ? "text-green-400" : "text-red-400"}>
                  {riskChecks[i] ? "✓" : "✗"}
                </span>
                <span className={riskChecks[i] ? "text-zinc-300" : "text-zinc-500"}>
                  {check.label}
                </span>
              </li>
            ))}
          </ul>
          <div className={`mt-4 px-3 py-2 rounded-lg text-sm font-semibold ${
            result.riskApproved ? "bg-green-500/20 text-green-300" : "bg-red-500/20 text-red-300"
          }`}>
            {result.riskApproved ? "✓ Approved" : `✗ Rejected — ${result.riskRejectReason}`}
          </div>
        </div>

        <div className="rounded-xl border border-zinc-700 bg-zinc-800 p-5">
          <h3 className="text-zinc-300 font-semibold mb-3">⚡ Trade Executor</h3>
          <div className="flex flex-col gap-2 text-sm">
            <div className="flex justify-between">
              <span className="text-zinc-500">Mode</span>
              <span className="font-mono text-zinc-200">{result.tradeMode}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Action</span>
              <span className="font-mono text-zinc-200">{result.tradeAction}</span>
            </div>
            {result.riskApproved && (
              <div className="flex justify-between">
                <span className="text-zinc-500">Order size</span>
                <span className="font-mono text-zinc-200">${result.orderSize}.00</span>
              </div>
            )}
          </div>
          <div className={`mt-4 px-3 py-2 rounded-lg text-sm font-semibold ${
            result.riskApproved && result.recommendation !== "HOLD"
              ? "bg-teal-500/20 text-teal-300"
              : "bg-zinc-700 text-zinc-400"
          }`}>
            {result.riskApproved && result.recommendation !== "HOLD"
              ? `✓ Order placed (demo)`
              : "No order placed"}
          </div>
        </div>
      </div>
    </div>
  );
}