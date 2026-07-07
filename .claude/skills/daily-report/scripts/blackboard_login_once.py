#!/usr/bin/env python3
"""One-time interactive login to blackboard.hcmiu.edu.vn.

Opens a real (non-headless) browser so the user can complete SSO / 2FA
manually. On success, saves the authenticated session to
~/.config/daily-report/blackboard_state.json for reuse by
blackboard_scrape.py. Never stores the password itself.
"""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

BLACKBOARD_URL = "https://blackboard.hcmiu.edu.vn"
STATE_DIR = Path.home() / ".config" / "daily-report"
STATE_FILE = STATE_DIR / "blackboard_state.json"


def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(BLACKBOARD_URL)
        print("Đăng nhập thủ công (bao gồm 2FA nếu có), rồi nhấn Enter tại đây khi đã vào được trang chủ Blackboard.")
        input()
        context.storage_state(path=str(STATE_FILE))
        browser.close()
    print(f"Đã lưu session tại {STATE_FILE}")


if __name__ == "__main__":
    main()
