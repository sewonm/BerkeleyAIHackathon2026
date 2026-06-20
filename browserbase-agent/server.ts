/**
 * Browserbase Research Agent — Express server
 * Runs on port 3001. Called by Vepaul's coordinator_agent.py.
 *
 * START:
 *   npm install
 *   npx ts-node server.ts
 *
 * OR build first:
 *   npm run build && npm start
 */

import express, { Request, Response } from "express";
import { browserbaseResearchAgent, ResearchAgentInput } from "./browserbaseResearchAgent";

const app = express();
app.use(express.json());

const PORT = process.env.PORT ?? 3001;

// ── Health check ──────────────────────────────────────────────────────────

app.get("/health", (_req: Request, res: Response) => {
  res.json({
    status: "ok",
    agent: "browserbase_research_agent",
    browserbase_key_set: !!process.env.BROWSERBASE_API_KEY,
  });
});

// ── Main research endpoint ────────────────────────────────────────────────
// POST /browserbase-research
// Called by coordinator_agent.py with market_question, teams, sport

app.post("/browserbase-research", async (req: Request, res: Response) => {
  const { market_question, teams, sport } = req.body as ResearchAgentInput;

  if (!market_question || !teams || !sport) {
    res.status(400).json({
      error: "missing_fields",
      required: ["market_question", "teams", "sport"],
      received: req.body,
    });
    return;
  }

  console.log(`[browserbase-agent] Researching: ${market_question}`);

  try {
    const result = await browserbaseResearchAgent({ market_question, teams, sport });
    console.log(`[browserbase-agent] Done — ${result.claims.length} claims, ${result.raw_tokens_total} raw tokens → ${result.compressed_tokens_total} compressed`);
    res.json(result);
  } catch (err) {
    console.error("[browserbase-agent] Error:", err);
    res.status(500).json({
      error: "research_failed",
      details: String(err),
    });
  }
});

app.listen(PORT, () => {
  console.log(`Browserbase Research Agent running on http://localhost:${PORT}`);
  console.log(`  Health: GET  http://localhost:${PORT}/health`);
  console.log(`  Research: POST http://localhost:${PORT}/browserbase-research`);
  console.log(`  BROWSERBASE_API_KEY: ${process.env.BROWSERBASE_API_KEY ? "SET" : "NOT SET (mock mode)"}`);
});
