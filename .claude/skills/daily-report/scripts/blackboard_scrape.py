#!/usr/bin/env python3
"""Scrape upcoming deadlines/announcements from blackboard.hcmiu.edu.vn.

Requires a saved Playwright storage state from blackboard_login_once.py at
~/.config/daily-report/blackboard_state.json (contains session cookies —
never commit this file).

Prints a JSON list of {"course": str, "title": str, "due_date": str, "url": str}.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BLACKBOARD_URL = "https://blackboard.hcmiu.edu.vn"
STATE_FILE = Path.home() / ".config" / "daily-report" / "blackboard_state.json"


def scrape_todo(page):
    """Scrape the Ultra 'To Do' stream for upcoming items.

    Selectors are best-effort for Blackboard Ultra's default theme and may
    need adjusting if HCMIU customizes the layout.
    """
    page.goto(f"{BLACKBOARD_URL}/ultra/stream")
    page.wait_for_load_state("networkidle")
    items = page.locator("[data-automation-id='streamItem']")
    count = items.count()
    results = []
    for i in range(count):
        item = items.nth(i)
        text = item.inner_text()
        link = item.locator("a").first
        href = link.get_attribute("href") if link.count() else None
        results.append({
            "course": "",
            "title": text.split("\n")[0] if text else "",
            "due_date": "",
            "url": f"{BLACKBOARD_URL}{href}" if href and href.startswith("/") else href,
        })
    return results


def main():
    if not STATE_FILE.exists():
        print(json.dumps({
            "error": f"no saved session at {STATE_FILE}; run blackboard_login_once.py first"
        }))
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(STATE_FILE))
        page = context.new_page()
        try:
            results = scrape_todo(page)
        finally:
            browser.close()

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
