#!/usr/bin/env python3
"""
Demo script for the Action Debug Runner.

Usage:
  export FIRECRAWL_API_KEY=fc-...
  poetry run python scripts/demo_debug_run.py

Runs two scenarios against example.com:
  1. Passing sequence (code steps)
  2. Failing sequence (bad selector in code) to show step-level diagnostics
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.schemas import DebugStep
from app.services.debug_runner import run_debug_sequence


def print_report(title: str, report) -> None:
    print(f"\n{'=' * 60}")
    print(title)
    print(f"{'=' * 60}")
    payload = report.model_dump()
    for step in payload.get("steps", []):
        if step.get("screenshot_base64"):
            step["screenshot_base64"] = f"<{len(step['screenshot_base64'])} chars>"
    print(json.dumps(payload, indent=2))


def main() -> int:
    if not os.getenv("FIRECRAWL_API_KEY"):
        print("Set FIRECRAWL_API_KEY before running the demo.", file=sys.stderr)
        return 1

    url = "https://example.com"

    passing_steps = [
        DebugStep(code="await page.waitForLoadState('networkidle'); true"),
        DebugStep(code="await page.evaluate(() => window.scrollBy(0, 300)); true"),
        DebugStep(code="await page.waitForTimeout(500); true"),
    ]

    failing_steps = [
        DebugStep(code="await page.waitForTimeout(500); true"),
        DebugStep(code="await page.click('.this-selector-does-not-exist'); true"),
        DebugStep(code="await page.waitForTimeout(500); true"),
    ]

    print_report("Scenario 1: all steps pass", run_debug_sequence(url, passing_steps))
    print_report("Scenario 2: step 2 fails", run_debug_sequence(url, failing_steps))

    print("\nDemo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
