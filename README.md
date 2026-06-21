# FirecrawlChallenge

**Action Debug Runner** — debug multi-step Firecrawl `/interact` workflows step-by-step.

Built for [Firecrawl Feedback #7](CHALLENGEDOC.md): when a 14-step action chain fails, find **which step broke** instead of one opaque `SCRAPE_FAILED`.

See [ONEPAGER.md](./ONEPAGER.md) for what was built, what was skipped, and why.

## What it does

1. Accept a full Playwright / agent-browser script
2. Split it into isolated `/interact` steps via Claude
3. Run each step sequentially against a live Firecrawl browser session
4. Return a debug report with `failed_at_step`, per-step errors, output, and `live_view_url`

## Quick start (Docker)

From the repo root:

```bash
cp docker-compose.override.yaml.example docker-compose.override.yaml
```

Edit `docker-compose.override.yaml` and set your API keys (this file is gitignored — never commit real keys):

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

Try **`POST /debug/interact/code`** from the Swagger UI or:

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

Both keys are required for the full code-block flow. Set them in `docker-compose.override.yaml` for Docker, or export them in your shell for local Poetry runs.

| Variable            | Required | Purpose                        |
| ------------------- | -------- | ------------------------------ |
| `FIRECRAWL_API_KEY` | Yes      | Scrape + `/interact` execution |
| `ANTHROPIC_API_KEY` | Yes      | Claude code splitting          |

`docker-compose.yaml` ships with placeholders; **`docker-compose.override.yaml` is where you put real values** (see `docker-compose.override.yaml.example`).

## Project layout

```
backend/api/
├── app/
│   ├── routers/debug.py              # POST /debug/interact/code
│   ├── controllers/                  # Orchestration + HTTP error mapping
│   ├── services/
│   │   ├── code_splitter.py          # Claude structured split
│   │   ├── code_split_result_builder.py
│   │   └── debug_runner.py           # Step-by-step /interact execution
│   ├── helpers/firecrawl.py          # Scrape ID + interact response parsing
│   ├── constants/code_splitter.py    # Claude prompts
│   └── models/                       # Request/response + split schemas
└── tests/
```

## Successful Runs

Example payloads for **`POST /debug/interact/code`** — all three run the same [Hacker News](https://news.ycombinator.com) workflow in different `/interact` languages:

1. Open the homepage (via `/scrape` on `url`)
2. Click **new** to go to `/newest`
3. Click the **first story** on the listing
4. Return the destination page title and URL

| Language | Style                                           | Notes                                                         |
| -------- | ----------------------------------------------- | ------------------------------------------------------------- |
| `node`   | Full Playwright script with `chromium.launch()` | Works when pasted as-is; Claude splits it into isolated steps |
| `python` | Playwright async against the pre-wired `page`   | Idiomatic for `/interact` — no browser launch                 |
| `bash`   | `agent-browser` CLI (`find`, `eval`, `wait`)    | Uses `eval` where shell state cannot carry between steps      |

On success, expect `status: "completed"`, multiple `passed` steps, and final `output` / `page_content` with the clicked story’s title and URL. To demo a failure, change a selector (e.g. `.titleline a` → `.does-not-exist`) and check `failed_at_step` plus the step’s `error` and `live_view_url`.

### `node`

```
{
  "url": "https://news.ycombinator.com",
  "code_block": "const { chromium } = require('playwright');\n\n(async () => {\n  const browser = await chromium.launch({ headless: false });\n  const page = await browser.newPage();\n\n  // Open Hacker News\n  await page.goto('https://news.ycombinator.com', { timeout: 3000 });\n  await page.waitForLoadState('domcontentloaded', { timeout: 3000 });\n\n  // Click New\n  await page.click(\n    '#hnmain > tbody > tr:nth-child(1) > td > table > tbody > tr > td:nth-child(2) > span > a:nth-child(2)',\n    { timeout: 3000 }\n  );\n\n  await page.waitForLoadState('domcontentloaded', { timeout: 3000 });\n\n  // Click first news item\n  await page.click(\n    '.titleline a',\n    { timeout: 3000 }\n  );\n\n  await page.waitForLoadState('domcontentloaded', { timeout: 3000 });\n\n  console.log({\n    title: await page.title(),\n    url: page.url()\n  });\n\n  await browser.close();\n})();",
  "language": "node"
}
```

### `python`

```
{
  "url": "https://news.ycombinator.com",
  "code_block": "import json\n\nawait page.wait_for_load_state('domcontentloaded')\n\n# Click \"new\"\nawait page.click('a[href=\"newest\"]')\n\nawait page.wait_for_load_state('domcontentloaded')\n\n# First story link\nfirst_story = page.locator('.titleline a').first\n\ntitle = await first_story.text_content()\nhref = await first_story.get_attribute('href')\n\nawait first_story.click()\n\nawait page.wait_for_load_state('domcontentloaded')\n\nprint(json.dumps({\n    'clicked_title': title,\n    'original_href': href,\n    'current_url': page.url,\n    'page_title': await page.title()\n}))",
  "language": "python"
}
```

### `bash`

```
{
  "url": "https://news.ycombinator.com",
  "code_block": "agent-browser wait --load domcontentloaded\n\nagent-browser find text \"new\" click\n\nagent-browser wait --load domcontentloaded\n\nagent-browser eval \"const link = document.querySelector('.titleline a'); const title = link?.textContent?.trim() ?? ''; const href = link?.href ?? ''; link?.click(); JSON.stringify({ clicked_title: title, original_href: href })\"\n\nagent-browser wait --load domcontentloaded\n\nagent-browser eval \"JSON.stringify({ current_url: location.href, page_title: document.title })\"",
  "language": "bash"
}
```
