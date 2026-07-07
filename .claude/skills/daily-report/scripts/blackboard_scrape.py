#!/usr/bin/env python3
"""Log in to blackboard.hcmiu.edu.vn and list upcoming deadlines/announcements.

No browser needed — HCMIU's Blackboard uses the classic (non-Ultra) login
form, so a plain HTTP session with cookies is enough. Credentials are read
from environment variables only:
  BLACKBOARD_USERNAME, BLACKBOARD_PASSWORD

Prints a JSON list of {"title": str, "url": str, "raw": str}.
"""
import http.cookiejar
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://blackboard.hcmiu.edu.vn"

_ca_bundle = "/root/.ccr/ca-bundle.crt"
_ctx = ssl.create_default_context(cafile=_ca_bundle if os.path.exists(_ca_bundle) else None)
_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

_jar = http.cookiejar.CookieJar()
_handlers = [
    urllib.request.HTTPCookieProcessor(_jar),
    urllib.request.HTTPSHandler(context=_ctx),
]
if _proxy:
    _handlers.append(urllib.request.ProxyHandler({"https": _proxy, "http": _proxy}))
_opener = urllib.request.build_opener(*_handlers)
_opener.addheaders = [("User-Agent", "Mozilla/5.0 (daily-report-skill)")]


def get(url: str) -> str:
    with _opener.open(url, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def post(url: str, data: dict) -> str:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with _opener.open(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def login(username: str, password: str):
    login_page = get(f"{BASE}/webapps/login/")
    m = re.search(
        r"name='blackboard\.platform\.security\.NonceUtil\.nonce' value='([^']+)'",
        login_page,
    )
    if not m:
        raise RuntimeError("Không tìm thấy nonce trên trang đăng nhập — trang có thể đã đổi cấu trúc.")
    nonce = m.group(1)

    result = post(f"{BASE}/webapps/login/", {
        "user_id": username,
        "password": password,
        "action": "login",
        "new_loc": "",
        "blackboard.platform.security.NonceUtil.nonce": nonce,
    })
    if "loginErrorMessage" in result or "Đăng nhập không thành công" in result:
        raise RuntimeError("Đăng nhập thất bại — kiểm tra lại BLACKBOARD_USERNAME/PASSWORD.")
    return result


def list_announcements():
    """Scrape the classic 'My Announcements' module on the portal homepage."""
    html = get(f"{BASE}/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_1_1")
    items = []
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{3,150})</a>', html):
        href, text = m.groups()
        text = text.strip()
        if not text or "javascript:" in href:
            continue
        items.append({"title": text, "url": href if href.startswith("http") else f"{BASE}{href}"})
    return items[:30]


def main():
    username = os.environ.get("BLACKBOARD_USERNAME")
    password = os.environ.get("BLACKBOARD_PASSWORD")
    if not username or not password:
        print(json.dumps({"error": "missing BLACKBOARD_USERNAME or BLACKBOARD_PASSWORD"}))
        sys.exit(1)

    try:
        login(username, password)
        results = list_announcements()
    except (RuntimeError, urllib.error.URLError) as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
