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
# HCMIU's Blackboard server only offers legacy ciphers (e.g. DHE-RSA-AES128-SHA);
# OpenSSL 3.x's default security level rejects those unless lowered.
_ctx.set_ciphers("DEFAULT@SECLEVEL=1")
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
    """Scrape 'My Announcements' — real course/system announcements, not nav links."""
    html = get(
        f"{BASE}/webapps/blackboard/execute/announcement"
        f"?method=search&context=mybb&handle=my_announcements"
    )
    items = []
    for li in re.finditer(r'<li class="clearfix"\s+id="([^"]+)">(.*?)</li>', html, re.S):
        item_id, block = li.groups()
        title_m = re.search(r'<h3[^>]*>\s*(.*?)\s*</h3>', block, re.S)
        posted_m = re.search(r'Posted on:\s*([^<]+)</span>', block)
        by_m = re.search(r'Posted by:</span>\s*([^<]+)', block)
        if not title_m:
            continue
        items.append({
            "id": item_id,
            "title": re.sub(r"\s+", " ", title_m.group(1)).strip(),
            "posted_on": posted_m.group(1).strip() if posted_m else "",
            "posted_by": by_m.group(1).strip() if by_m else "",
        })
    return items


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
