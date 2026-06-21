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
