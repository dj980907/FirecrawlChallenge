# Action Debug Runner: One Pager

## The Problem

A workflow automation startup on Firecrawl's growth plan runs fourteen-step vendor-dashboard scrapes: click, wait, fill, scroll, execute JavaScript, repeat. It mostly works. When it doesn't, the entire chain returns one `SCRAPE_FAILED`:

> _"Fourteen steps, one error. Was it step three or step eleven? Did a selector miss, did a wait time out, did the page change on us? We re-run the entire chain with screenshots sprinkled in just to find out where it died. Re-run and squint, that's our debugging strategy."_

They asked for two things: **which step failed**, and **what the page looked like when it did**. Even the step index alone, they said, would cut debugging time in half.

This is **Feedback #7**. `/interact` already gives step-level control; what's missing is step-level **observability**: a structured report instead of a single opaque error.

---

## Why I Chose #7

Eleven feedback items, 72 hours. I picked the problem that was **frequent**, **buildable** with existing APIs and **not already solved** by the product.

**Support data (`data/tickets.csv`, last 90 days):** 214 of 535 tickets (~40%) are "error confusion / debugging help", more than double the next category (96 protected-site failures). Customers aren't just hitting errors; they can't tell _where_ in a workflow the error happened. #7 names that gap directly.

**Account data (`data/accounts.csv`):** The #7 caller is a growth-plan customer ($28k ARR, usage up 6%, heavy actions usage), already running the kind of multi-step chains this demo targets, with usage still climbing.

I almost built **#9** instead. That customer wants extractors that maintain themselves: describe the data once, stop owning upkeep when sites change. My idea was a self-correcting extraction layer on top of Firecrawl's existing `/monitor`: Monitor already watches for drift; when extraction output stops matching the schema, the layer would re-scrape, re-prompt, validate, and update the extractor automatically. That is a real product direction, and #9's customer would pay for it. I passed because the repair loop (detect → diagnose → regenerate → redeploy) is a bigger surface than I could ship cleanly in 72 hours, while `/monitor` already covers the detection half. #7 had the same API footprint with a tighter demo: one failing fourteen-step script, one JSON report, no persistent job registry.

#7 sits where ticket volume, a paying actions customer, and an unfilled product gap overlap.

---

## What I Built

**Action Debug Runner**: a FastAPI API with two endpoints:

- **`POST /debug/scrape/actions`** — paste the customer's Firecrawl scrape `actions` array (click, wait, write, scroll, executeJavascript, etc.). Each action compiles to an isolated `/interact` step and runs sequentially.
- **`POST /debug/interact/code`** — paste a full Playwright or agent-browser script. Claude splits it into `/interact` steps.

Both return the same debug report shape.

| Customer ask                    | What the API returns                                                   |
| ------------------------------- | ---------------------------------------------------------------------- |
| Which step failed?              | `failed_at_step` + per-step `status` (`passed` / `failed` / `skipped`) |
| Step index alone is enough      | 1-based index on first failure; later steps marked `skipped`           |
| What did the page look like?    | `live_view_url` from `/interact` on the failing step                   |
| Fourteen-step scripts           | `parsed_steps` + `step_summaries` (from AI split or action labels)     |
| Stop re-running the whole chain | One call → full timeline, errors, and output per step                  |

**Request (scrape actions — #7's native input):**

```json
{
  "url": "https://news.ycombinator.com",
  "language": "node",
  "actions": [
    { "type": "click", "selector": "a[href=\"newest\"]" },
    { "type": "wait", "selector": ".titleline a" },
    { "type": "click", "selector": ".titleline a" },
    {
      "type": "executeJavascript",
      "script": "JSON.stringify({ title: document.title, url: location.href })"
    }
  ]
}
```

**Request (Playwright script):**

```json
{
  "url": "https://news.ycombinator.com",
  "code_block": "await page.click('a[href=\"newest\"]');\nJSON.stringify({ ok: true });",
  "language": "node"
}
```

`language`: `node` (default), `python`, or `bash`.

**Pipeline:**

1. **Actions path:** compile each action to `/interact` code (deterministic; no Claude)
2. **Code path:** Claude splits the script (respecting isolated `/interact` contexts: only the DOM persists, not variables)
3. Each intermediate step gets a success sentinel (`; true`, `\nTrue`, or `\ntrue`)
4. `/scrape` opens the browser → each step runs via `/interact` → first failure stops the run → `stop_interaction` cleans up

---

## What I Deliberately Did Not Build

Scoped to what #7 asked for: find the failing step and see the page at failure. Everything below is follow-on work I considered and cut.

**Prompt or pre-split step inputs.** I dropped alternate endpoints that accepted a natural-language prompt or an explicit step list. The two supported inputs are scrape `actions[]` and a full code block.

**Byte-identical scrape `actions` execution.** The actions endpoint compiles each action to `/interact` code and runs step-by-step. That gives the observability #7 asked for, but timing and semantics may differ slightly from one monolithic `/scrape` call with a fourteen-step array. Prefix re-scrapes or native `failedActionIndex` from Firecrawl would be needed for prod-parity.

**Screenshot capture on failure.** `/interact` already returns `liveViewUrl` on the failing step, which answers "what did the page look like?" Base64 screenshots would duplicate that signal and add latency and storage for a 72-hour API demo.

**Auto-fixing broken selectors.** Knowing step 11 failed is different from fixing the selector. Self-healing would turn this into remediation (#9 territory). #7 only asked for observability.

**Dashboard or run history.** The repo includes a Next.js starter shell, but the product surface is the debug JSON report from `/debug/scrape/actions` and `/debug/interact/code`. Runs are stateless: no database, no saved timelines. That matches debugging one broken workflow in CI or a REPL, not operating a monitoring product.

**The #9 self-correcting extraction layer.** See above: `/monitor` plus autonomous repair is the bigger bet I almost took instead of this.

**Other feedback items (#2 proxy controls, #10 LinkedIn, #11 authenticated sessions).** These need platform work (residential proxy plumbing, anti-bot, credential vaults), not an app layer on top of existing APIs.

---

## One Thing AI Got Wrong

My first direction with AI coding tools was **#9**: a self-maintaining extraction layer on `/monitor` that detects schema drift, re-prompts, validates output, and redeploys fixed extractors without a human in the loop.

The models were fast and convincing. Within a couple hours of back and forth, I had a plausible architecture: Monitor watches pages, a validator compares JSON to the schema, Claude regenerates the extract prompt on mismatch, a dry-run scrape confirms the fix before swapping it in. On paper it mapped cleanly to what the customer asked for ("describe the data once… especially the maintains-itself part").

What AI got wrong was the **robustness bar**. "Maintains itself" is not a feature sketch; it is a reliability contract. False repairs (changing a working extractor because of noise), missed drift (silent wrong data), and runaway auto-fix loops all have to be ruled out before a customer would trust it with forty production jobs. That means validation gates, rollback, versioning, audit trails, and handling partial page redesigns, not a happy-path demo. The tools kept proposing the loop without accounting for how much engineering makes it **airtight**.

I caught it by trying to implement the repair path end-to-end. The happy path worked in an afternoon; the failure modes did not. In one test Monitor fired on a benign DOM change. In another, regenerated JSON passed schema validation but mapped fields to the wrong semantics. I was building ops infrastructure, not a scraper wrapper. Seventy-two hours could produce a flashy auto-fix demo. It could not produce something I would hand to the #9 customer who spends "one engineer's Fridays, forever" on upkeep.

That is when I switched to **#7**. Step-level debugging is narrow, testable, and demoable in one API call, with a clear definition of done. AI was useful for scaffolding both ideas. It was wrong about which one was actually shippable in the time box.
