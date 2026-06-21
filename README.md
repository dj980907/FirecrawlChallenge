# FirecrawlChallenge

**Action Debug Runner**: debug multi-step Firecrawl `/interact` workflows step-by-step.

Built for [Firecrawl Feedback #7](CHALLENGEDOC.md): when a 14-step action chain fails, find **which step broke** instead of one opaque `SCRAPE_FAILED`.

See [ONEPAGER.md](./ONEPAGER.md) for what was built, what was skipped, and why.

## What it does

Two input modes, one debug report:

1. **Scrape `actions[]`** (`POST /debug/scrape/actions`) — paste the Firecrawl scrape actions array (click, wait, write, scroll, executeJavascript, …). Each action compiles to an isolated `/interact` step.
2. **Playwright script** (`POST /debug/interact/code`) — paste a full script; Claude splits it into `/interact` steps.

Both run sequentially against a live Firecrawl browser session and return `failed_at_step`, per-step errors, output, and `live_view_url`.

## Quick start (Docker)

From the repo root:

```bash
cp docker-compose.override.yaml.example docker-compose.override.yaml
```

Edit `docker-compose.override.yaml` and set your API keys (this file is gitignored; never commit real keys):

```yaml
services:
  api:
    environment:
      - FIRECRAWL_API_KEY=fc-your-api-key-here
      - ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

Start the stack:

```bash
docker compose up --build
```

| Service           | URL                           |
| ----------------- | ----------------------------- |
| API docs          | http://api.localhost/docs     |
| Frontend          | http://localhost:3000         |
| Traefik dashboard | http://traefik.localhost:8080 |

Try **`POST /debug/scrape/actions`** (Feedback #7's native input) or **`POST /debug/interact/code`** from the Swagger UI.

### Scrape actions array

Supported action types: `wait`, `click`, `write`, `press`, `scroll`, `scrape`, `executeJavascript`, `screenshot`. (`pdf` is rejected at compile time.)

See [Successful Runs](#scrape-actions-array-1) below for full example payloads. Quick curl:

```bash
curl -s -X POST http://api.localhost/debug/scrape/actions \
  -H "Content-Type: application/json" \
  -d @- <<'EOF' | jq
{
  "url": "https://news.ycombinator.com",
  "language": "node",
  "actions": [
    { "type": "wait", "milliseconds": 800 },
    { "type": "scroll", "direction": "down" },
    { "type": "wait", "selector": "#hnmain" },
    {
      "type": "executeJavascript",
      "script": "window.__debug = { startUrl: location.href }; true"
    },
    { "type": "click", "selector": "a[href=\"newest\"]" },
    { "type": "wait", "milliseconds": 600 },
    { "type": "wait", "selector": ".titleline a" },
    { "type": "scroll", "direction": "down" }
  ]
}
EOF
```

### Playwright code block

```bash
curl -s -X POST http://api.localhost/debug/interact/code \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "code_block": "await page.click(\"#login\");\nJSON.stringify({ ok: true });",
    "language": "node"
  }' | jq
```

Supported languages: `node` (default), `python`, `bash`.

## Quick start (API only, no Docker)

```bash
cd backend/api
poetry install
export FIRECRAWL_API_KEY=fc-...
export ANTHROPIC_API_KEY=sk-ant-...
poetry run uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs.

## Environment variables

Both keys are required for **`/debug/interact/code`**. Only `FIRECRAWL_API_KEY` is required for **`/debug/scrape/actions`**.

| Variable            | Required       | Purpose                        |
| ------------------- | -------------- | ------------------------------ |
| `FIRECRAWL_API_KEY` | Yes            | Scrape + `/interact` execution |
| `ANTHROPIC_API_KEY` | Code path only | Claude code splitting          |

`docker-compose.yaml` ships with placeholders; **`docker-compose.override.yaml` is where you put real values** (see `docker-compose.override.yaml.example`).

## Project layout

```
backend/api/
├── app/
│   ├── routers/debug.py              # POST /debug/scrape/actions, /debug/interact/code
│   ├── controllers/                  # Orchestration + HTTP error mapping
│   ├── services/
│   │   ├── actions_compiler.py       # scrape actions[] → /interact steps
│   │   ├── code_splitter.py          # Claude structured split
│   │   ├── code_split_result_builder.py
│   │   └── debug_runner.py           # Step-by-step /interact execution
│   ├── helpers/firecrawl.py          # Scrape ID + interact response parsing
│   ├── constants/code_splitter.py    # Claude prompts
│   └── models/                       # Request/response + action/split schemas
└── tests/
```

## Successful Runs

### Scrape actions array

Example payloads for **`POST /debug/scrape/actions`**. Eight-step [Hacker News](https://news.ycombinator.com) workflow mixing `wait`, `scroll`, `executeJavascript`, and `click` (Feedback #7-style action chain).

On success, expect `status: "completed"` and all eight steps `passed`.

#### Success

```json
{
  "url": "https://news.ycombinator.com",
  "language": "node",
  "actions": [
    { "type": "wait", "milliseconds": 800 },
    { "type": "scroll", "direction": "down" },
    { "type": "wait", "selector": "#hnmain" },
    {
      "type": "executeJavascript",
      "script": "window.__debug = { startUrl: location.href }; true"
    },
    { "type": "click", "selector": "a[href=\"newest\"]" },
    { "type": "wait", "milliseconds": 600 },
    { "type": "wait", "selector": ".titleline a" },
    { "type": "scroll", "direction": "down" }
  ]
}
```

#### Failure test

Step 5 uses a bad selector. Expect `status: "failed"`, `failed_at_step: 5`, an `error` and `live_view_url` on that step, and steps 6–8 marked `skipped`.

```json
{
  "url": "https://news.ycombinator.com",
  "actions": [
    { "type": "wait", "milliseconds": 800 },
    { "type": "scroll", "direction": "down" },
    { "type": "wait", "selector": "#hnmain" },
    {
      "type": "executeJavascript",
      "script": "window.__debug = { startUrl: location.href }; true"
    },
    { "type": "click", "selector": ".this-selector-does-not-exist" },
    { "type": "wait", "milliseconds": 600 },
    { "type": "wait", "selector": ".titleline a" },
    { "type": "scroll", "direction": "down" }
  ]
}
```

(`language` defaults to `node` when omitted.)

### Playwright code block

Example payloads for **`POST /debug/interact/code`**. All three run the same [Hacker News](https://news.ycombinator.com) workflow in different `/interact` languages:

1. Open the homepage (via `/scrape` on `url`)
2. Click **new** to go to `/newest`
3. Click the **first story** on the listing
4. Return the destination page title and URL

| Language | Style                                           | Notes                                                         |
| -------- | ----------------------------------------------- | ------------------------------------------------------------- |
| `node`   | Full Playwright script with `chromium.launch()` | Works when pasted as-is; Claude splits it into isolated steps |
| `python` | Playwright async against the pre-wired `page`   | Idiomatic for `/interact`; no browser launch                  |
| `bash`   | `agent-browser` CLI (`find`, `eval`, `wait`)    | Uses `eval` where shell state cannot carry between steps      |

On success, expect `status: "completed"`, multiple `passed` steps, and final `output` / `page_content` with the clicked story's title and URL.

### `node`

```json
{
  "url": "https://news.ycombinator.com",
  "code_block": "const { chromium } = require('playwright');\n\n(async () => {\n  const browser = await chromium.launch({ headless: false });\n  const page = await browser.newPage();\n\n  // Open Hacker News\n  await page.goto('https://news.ycombinator.com', { timeout: 3000 });\n  await page.waitForLoadState('domcontentloaded', { timeout: 3000 });\n\n  // Click New\n  await page.click(\n    '#hnmain > tbody > tr:nth-child(1) > td > table > tbody > tr > td:nth-child(2) > span > a:nth-child(2)',\n    { timeout: 3000 }\n  );\n\n  await page.waitForLoadState('domcontentloaded', { timeout: 3000 });\n\n  // Click first news item\n  await page.click(\n    '.titleline a',\n    { timeout: 3000 }\n  );\n\n  await page.waitForLoadState('domcontentloaded', { timeout: 3000 });\n\n  console.log({\n    title: await page.title(),\n    url: page.url()\n  });\n\n  await browser.close();\n})();",
  "language": "node"
}
```

### `python`

```json
{
  "url": "https://news.ycombinator.com",
  "code_block": "import json\n\nawait page.wait_for_load_state('domcontentloaded')\n\n# Click \"new\"\nawait page.click('a[href=\"newest\"]')\n\nawait page.wait_for_load_state('domcontentloaded')\n\n# First story link\nfirst_story = page.locator('.titleline a').first\n\ntitle = await first_story.text_content()\nhref = await first_story.get_attribute('href')\n\nawait first_story.click()\n\nawait page.wait_for_load_state('domcontentloaded')\n\nprint(json.dumps({\n    'clicked_title': title,\n    'original_href': href,\n    'current_url': page.url,\n    'page_title': await page.title()\n}))",
  "language": "python"
}
```

### `bash`

```json
{
  "url": "https://news.ycombinator.com",
  "code_block": "agent-browser wait --load domcontentloaded\n\nagent-browser find text \"new\" click\n\nagent-browser wait --load domcontentloaded\n\nagent-browser eval \"const link = document.querySelector('.titleline a'); const title = link?.textContent?.trim() ?? ''; const href = link?.href ?? ''; link?.click(); JSON.stringify({ clicked_title: title, original_href: href })\"\n\nagent-browser wait --load domcontentloaded\n\nagent-browser eval \"JSON.stringify({ current_url: location.href, page_title: document.title })\"",
  "language": "bash"
}
```
