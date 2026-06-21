# Action Debug Runner — One Pager

## What I Built

**Action Debug Runner** — a FastAPI service that debugs multi-step Firecrawl `/interact` workflows step-by-step.

Paste a full Playwright or agent-browser script at **`POST /debug/interact/code`**. Claude splits it into isolated `/interact` steps, the runner executes each one in order, and the API returns a structured debug report.

When something breaks, you get:

- **`failed_at_step`** — 1-based index of the first failing step
- **Per-step status** — `passed`, `failed`, or `skipped`
- **The code** that ran for each step (`parsed_steps` + `step_summaries` from the AI split)
- **Error message** — stderr, exit code, or exception text for the failed step
- **`live_view_url`** — read-only browser stream from `/interact` at that moment
- **`output`** — whatever the step returned

This directly addresses **Feedback #7**:

> _"Fourteen steps, one error. Was it step three or step eleven? … Even just the step index would cut our debugging time in half."_

### API

**`POST /debug/interact/code`**

```json
{
  "url": "https://example.com",
  "code_block": "await page.click('#login');\nJSON.stringify({ ok: true });",
  "language": "node"
}
```

`language` is `"node"` (default), `"python"`, or `"bash"`.

**Response (abbreviated):**

```json
{
  "status": "failed",
  "failed_at_step": 2,
  "total_steps": 3,
  "total_duration_ms": 4200,
  "parsed_steps": [
    "await page.click('#login'); true",
    "JSON.stringify({ ok: true })"
  ],
  "step_summaries": ["Click login", "Return result"],
  "steps": [
    {
      "index": 1,
      "status": "passed",
      "duration_ms": 800,
      "live_view_url": "https://..."
    },
    {
      "index": 2,
      "status": "failed",
      "duration_ms": 1200,
      "error": "...",
      "live_view_url": "https://..."
    },
    { "index": 3, "status": "skipped", "duration_ms": 0 }
  ],
  "scrape_id": "..."
}
```

Open `/docs` for the full OpenAPI schema.

### How It Works

1. **Split** — Claude (`claude-sonnet-4-6`) parses the script into steps with rules for isolated `/interact` contexts (variables do not carry between steps; only the DOM persists).
2. **Prepare** — Each intermediate step gets a language-specific success sentinel (`; true`, `\nTrue`, or `\ntrue`) so it can run standalone.
3. **Scrape** — Open a live browser session via Firecrawl `/scrape`.
4. **Execute** — Run each step via `/interact` individually; record status, duration, output, and `liveViewUrl`.
5. **Stop early** — On first failure, mark remaining steps as `skipped`.
6. **Cleanup** — Always call `stop_interaction`.

### Architecture

```
Router → CodeBlockDebugController → CodeSplitter (Claude) → DebugRunner (Firecrawl)
                ↓
         DebugController (error mapping)
```

Layers: **router** (HTTP), **controllers** (orchestration + error mapping), **services** (splitting, step prep, sequential execution), **helpers** (Firecrawl response parsing), **models** (Pydantic schemas).

## What I Deliberately Did Not Build

- **Firecrawl `actions` array runner** — `/interact` takes prompt/code, not scrape action objects; callers paste scripts instead
- **Multiple input modes** (prompt-only, mixed, pre-split steps) — one code-block flow covers the #7 use case
- **Failure screenshots** — `/interact` already returns `liveViewUrl`; a base64 screenshot added latency and duplicate signal
- **Self-healing selectors** — useful follow-up, but step-level diagnostics solve the immediate pain
- **Persistent storage or dashboard** — the JSON report is the product surface

## Why This Problem

Feedback #7 is the sharpest unsolved pain in the set:

- Multi-step workflows fail as one opaque `SCRAPE_FAILED`
- `/interact` gives step-level control, but developers must orchestrate debugging themselves
- Nothing in Firecrawl today produces a **step-by-step debug report** from a sequence of interact calls

Other feedback items either already exist in the product (e.g. Monitor for #9), require platform-level work (#2 proxies, #10 LinkedIn), or are a different product surface (#4 latency modes).

## One Thing AI Got Wrong

While exploring Feedback #9, I initially proposed building "semantic change detection" on top of monitors. **That was wrong** — Firecrawl Monitor already supports JSON-mode change tracking, per-field diffs, goal-based judging, and snapshots. The real gap was not "what changed on the page," but **"which step broke, and what did the page look like when it did?"**

A second mistake during implementation: AI kept encoding `/interact` success sentinels (`; true`) in Claude's system prompt. **That belongs in deterministic post-processing** (`prepare_step_code`) — the model should focus on _where_ to split, not _how_ to suffix each step.
