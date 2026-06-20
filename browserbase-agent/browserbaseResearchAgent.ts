/**
 * Browserbase Research Agent
 *
 * Sub-agent called by Vepaul's orchestrator (coordinator_agent.py).
 * Takes a market question + sport context, searches the web, fetches
 * relevant pages, and returns structured evidence claims.
 *
 * INSTALL: npm install
 * ENV VARS: BROWSERBASE_API_KEY, BROWSERBASE_PROJECT_ID
 *
 * SDK DOCS: https://docs.browserbase.com/reference/sdk/nodejs
 */

import Browserbase from "@browserbasehq/sdk";

// ── Shared claim schema (matches everyone else's output) ──────────────────

export interface EvidenceClaim {
  claim: string;
  source_type: "web";
  source_name: string;
  supports: "yes" | "no" | "hold" | "neutral";
  confidence: number;       // 0–1
  market_relevance: number; // 0–1
  recency: "high" | "medium" | "low";
  raw_evidence: string;
  raw_tokens: number;
  compressed_tokens: number;
}

export interface ResearchAgentInput {
  market_question: string;
  teams: string[];
  sport: string;
}

export interface ResearchAgentOutput {
  agent: "browserbase_research_agent";
  market_question: string;
  raw_tokens_total: number;
  compressed_tokens_total: number;
  claims: EvidenceClaim[];
}

// ── Main agent function ───────────────────────────────────────────────────

export async function browserbaseResearchAgent(
  input: ResearchAgentInput
): Promise<ResearchAgentOutput> {
  const apiKey = process.env.BROWSERBASE_API_KEY;

  // Fall back to mock data if no API key (lets pipeline run without real credentials)
  if (!apiKey) {
    console.warn("[browserbase] No API key — returning mock claims");
    return mockOutput(input);
  }

  try {
    return await liveResearch(input, apiKey);
  } catch (err) {
    console.error("[browserbase] Live research failed, falling back to mock:", err);
    return mockOutput(input);
  }
}

// ── Live Browserbase path ─────────────────────────────────────────────────

async function liveResearch(
  input: ResearchAgentInput,
  apiKey: string
): Promise<ResearchAgentOutput> {
  const bb = new Browserbase({ apiKey });

  const teamStr = input.teams.join(" vs ");
  const queries = [
    `${input.sport} ${teamStr} injury report today`,
    `${input.sport} ${teamStr} lineup news prediction`,
    `${input.sport} ${teamStr} recent form stats`,
  ];

  const rawChunks: { title: string; url: string; text: string }[] = [];

  for (const query of queries) {
    // Step 1: Search — returns URLs + titles, no browser needed
    const searchResult = await bb.search.web({
      query,
      numResults: 3,
    });

    // Step 2: Fetch top result as clean markdown
    for (const result of searchResult.results.slice(0, 2)) {
      try {
        const fetched = await bb.fetchApi.create({
          url: result.url,
          format: "markdown",
        });
        rawChunks.push({
          title: result.title,
          url: result.url,
          text: (fetched.content ?? "").slice(0, 3000),
        });
      } catch {
        // skip failed fetches — don't abort the whole agent
      }
    }
  }

  // Step 3: Convert raw chunks into structured claims
  const claims = chunksToClaimsHeuristic(rawChunks, input);
  const rawTotal = claims.reduce((s, c) => s + c.raw_tokens, 0);
  const compressedTotal = claims.reduce((s, c) => s + c.compressed_tokens, 0);

  return {
    agent: "browserbase_research_agent",
    market_question: input.market_question,
    raw_tokens_total: rawTotal,
    compressed_tokens_total: compressedTotal,
    claims,
  };
}

// ── Heuristic claim extractor ─────────────────────────────────────────────
// Converts raw markdown chunks into structured claims.
// For the hackathon this is keyword-based. Later: swap in an LLM extraction call.

function chunksToClaimsHeuristic(
  chunks: { title: string; url: string; text: string }[],
  input: ResearchAgentInput
): EvidenceClaim[] {
  const claims: EvidenceClaim[] = [];

  const injuryKeywords = ["injury", "injured", "questionable", "doubtful", "out", "listed", "ankle", "knee", "calf", "hamstring"];
  const positiveKeywords = ["win", "favorite", "dominant", "strong", "healthy", "fit", "form"];
  const negativeKeywords = ["loss", "underdog", "weak", "struggling", "suspend"];

  for (const chunk of chunks) {
    const lines = chunk.text.split("\n").filter((l) => l.trim().length > 40);

    for (const line of lines.slice(0, 5)) {
      const lower = line.toLowerCase();
      const rawTokens = line.split(/\s+/).length;

      // Injury claim
      if (injuryKeywords.some((k) => lower.includes(k))) {
        const mentionedTeam = input.teams.find((t) => lower.includes(t.toLowerCase()));
        const supports = mentionedTeam === input.teams[0] ? "no" : "yes"; // injury to team_b helps team_a

        claims.push({
          claim: line.trim().slice(0, 200),
          source_type: "web",
          source_name: chunk.title,
          supports,
          confidence: 0.75,
          market_relevance: 0.88,
          recency: "high",
          raw_evidence: line.trim().slice(0, 300),
          raw_tokens: rawTokens,
          compressed_tokens: Math.round(rawTokens * 0.12),
        });
        continue;
      }

      // Positive signal for team_a
      if (positiveKeywords.some((k) => lower.includes(k)) && lower.includes(input.teams[0].toLowerCase())) {
        claims.push({
          claim: line.trim().slice(0, 200),
          source_type: "web",
          source_name: chunk.title,
          supports: "yes",
          confidence: 0.65,
          market_relevance: 0.72,
          recency: "medium",
          raw_evidence: line.trim().slice(0, 300),
          raw_tokens: rawTokens,
          compressed_tokens: Math.round(rawTokens * 0.12),
        });
        continue;
      }

      // Negative signal for team_a
      if (negativeKeywords.some((k) => lower.includes(k)) && lower.includes(input.teams[0].toLowerCase())) {
        claims.push({
          claim: line.trim().slice(0, 200),
          source_type: "web",
          source_name: chunk.title,
          supports: "no",
          confidence: 0.60,
          market_relevance: 0.65,
          recency: "medium",
          raw_evidence: line.trim().slice(0, 300),
          raw_tokens: rawTokens,
          compressed_tokens: Math.round(rawTokens * 0.12),
        });
      }
    }
  }

  // Always return at least 1 claim so the pipeline doesn't break
  if (claims.length === 0) {
    claims.push({
      claim: `No high-signal web evidence found for ${input.teams.join(" vs ")}. Recommend HOLD pending more data.`,
      source_type: "web",
      source_name: "browserbase_search",
      supports: "hold",
      confidence: 0.3,
      market_relevance: 0.4,
      recency: "low",
      raw_evidence: "No injury/form signals detected in top web results.",
      raw_tokens: 50,
      compressed_tokens: 8,
    });
  }

  return claims;
}

// ── Mock fallback ─────────────────────────────────────────────────────────

function mockOutput(input: ResearchAgentInput): ResearchAgentOutput {
  return {
    agent: "browserbase_research_agent",
    market_question: input.market_question,
    raw_tokens_total: 8400,
    compressed_tokens_total: 960,
    claims: [
      {
        claim: `${input.teams[1]}'s key player listed as questionable with an ankle injury per injury report.`,
        source_type: "web",
        source_name: "Mock injury report (set BROWSERBASE_API_KEY for live data)",
        supports: "yes",
        confidence: 0.82,
        market_relevance: 0.91,
        recency: "high",
        raw_evidence: "Questionable — ankle — did not practice Friday.",
        raw_tokens: 1200,
        compressed_tokens: 140,
      },
      {
        claim: `${input.teams[0]} have won 4 of their last 5 matches and rank higher in recent form.`,
        source_type: "web",
        source_name: "Mock stats feed",
        supports: "yes",
        confidence: 0.78,
        market_relevance: 0.82,
        recency: "high",
        raw_evidence: "Form: W W L W W. Current rank: 3rd vs 9th.",
        raw_tokens: 900,
        compressed_tokens: 110,
      },
      {
        claim: `Market analysts expect a close match but lean toward ${input.teams[0]} on current form.`,
        source_type: "web",
        source_name: "Mock analyst commentary",
        supports: "yes",
        confidence: 0.65,
        market_relevance: 0.70,
        recency: "medium",
        raw_evidence: "Slight edge to team A based on form and home advantage.",
        raw_tokens: 800,
        compressed_tokens: 95,
      },
    ],
  };
}
