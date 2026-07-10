#!/usr/bin/env python3
"""Detect Blackboard "What's New" style updates (grades, new content) via the
public REST API — a stable substitute for the bell-icon notification panel,
which is powered by an undocumented DWR endpoint that isn't safe to scrape.

Credentials from environment variables only: BLACKBOARD_USERNAME, BLACKBOARD_PASSWORD.

For each enrolled course, collects two kinds of signals:
  - content:{contentId} -> last "modified" timestamp (new/updated course materials)
  - grade:{columnId}    -> (score, changeIndex) (new/updated grades)

Prints a JSON list of {"course": str, "type": "content"|"grade", "title": str,
"detail": str}. Compare the returned items' identity+value against a saved
state file (same idea as blackboard_scrape.py's last_state.json) to detect
what's new since the last run.
"""
import http.cookiejar
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://blackboard.hcmiu.edu.vn"

_ca_bundle = "/root/.ccr/ca-bundle.crt"
_ctx = ssl.create_default_context(cafile=_ca_bundle if os.path.exists(_ca_bundle) else None)
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


def get(url: str, retries: int = 5):
    last_err = None
    for attempt in range(retries):
        try:
            with _opener.open(url, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as e:
            last_err = e
            time.sleep(0.5 * (attempt + 1))
            continue
    raise last_err


def get_json(url: str):
    result = json.loads(get(url))
    time.sleep(0.2)
    return result


def post(url: str, data: dict):
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
        raise RuntimeError("Không tìm thấy nonce trên trang đăng nhập.")
    nonce = m.group(1)
    result = post(f"{BASE}/webapps/login/", {
        "user_id": username,
        "password": password,
        "action": "login",
        "new_loc": "",
        "blackboard.platform.security.NonceUtil.nonce": nonce,
    })
    if "loginErrorMessage" in result:
        raise RuntimeError("Đăng nhập thất bại — kiểm tra lại BLACKBOARD_USERNAME/PASSWORD.")


def walk_contents(course_id, content_id, out, depth=0):
    if depth > 4:
        return
    try:
        data = get_json(f"{BASE}/learn/api/public/v1/courses/{course_id}/contents/{content_id}/children")
    except urllib.error.HTTPError:
        return
    for item in data.get("results", []):
        out.append({
            "id": item["id"],
            "title": item.get("title", ""),
            "modified": item.get("modified", ""),
        })
        if item.get("hasChildren"):
            walk_contents(course_id, item["id"], out, depth + 1)


def get_content_signals(course_id):
    out = []
    try:
        top = get_json(f"{BASE}/learn/api/public/v1/courses/{course_id}/contents")
    except urllib.error.HTTPError:
        return out
    for item in top.get("results", []):
        out.append({
            "id": item["id"],
            "title": item.get("title", ""),
            "modified": item.get("modified", ""),
        })
        if item.get("hasChildren"):
            walk_contents(course_id, item["id"], out)
    return out


def get_grade_signals(course_id, user_id):
    out = []
    try:
        columns = get_json(f"{BASE}/learn/api/public/v2/courses/{course_id}/gradebook/columns")
    except urllib.error.HTTPError:
        return out
    for col in columns.get("results", []):
        if col.get("grading", {}).get("type") == "Calculated":
            continue  # skip Total/Weighted Total, not a real assignment
        col_id = col["id"]
        try:
            grade = get_json(
                f"{BASE}/learn/api/public/v2/courses/{course_id}/gradebook/columns/{col_id}/users/{user_id}"
            )
        except urllib.error.HTTPError:
            continue
        out.append({
            "id": col_id,
            "title": col.get("name", ""),
            "score": grade.get("score"),
            "changeIndex": grade.get("changeIndex"),
        })
    return out


def main():
    username = os.environ.get("BLACKBOARD_USERNAME")
    password = os.environ.get("BLACKBOARD_PASSWORD")
    if not username or not password:
        print(json.dumps({"error": "missing BLACKBOARD_USERNAME or BLACKBOARD_PASSWORD"}))
        sys.exit(1)

    try:
        login(username, password)
        me = get_json(f"{BASE}/learn/api/public/v1/users/me")
        user_id = me["id"]
        enrollments = get_json(f"{BASE}/learn/api/public/v1/users/me/courses")
    except (RuntimeError, urllib.error.URLError) as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    items = []
    for enr in enrollments.get("results", []):
        if enr.get("availability", {}).get("available") != "Yes":
            continue
        course_id = enr["courseId"]
        try:
            course = get_json(f"{BASE}/learn/api/public/v3/courses/{course_id}")
            course_name = course.get("name", course_id)
        except urllib.error.HTTPError:
            course_name = course_id

        for c in get_content_signals(course_id):
            items.append({
                "course": course_name,
                "type": "content",
                "title": c["title"],
                "id": f"content:{c['id']}",
                "value": c["modified"],
            })
        for g in get_grade_signals(course_id, user_id):
            if g["score"] is None:
                continue  # not graded yet, nothing to report
            items.append({
                "course": course_name,
                "type": "grade",
                "title": g["title"],
                "id": f"grade:{g['id']}",
                "value": f"{g['score']}|{g['changeIndex']}",
            })

    print(json.dumps(items, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
