#!/usr/bin/env python3
"""One-time device-code login to obtain a Microsoft Graph refresh token.

Reads MS_CLIENT_ID / MS_TENANT_ID from env vars, prints a verification URL
and code for the user to complete sign-in in their own browser, then prints
the resulting refresh_token (store it as MS_REFRESH_TOKEN; do not commit it).
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SCOPES = "https://graph.microsoft.com/Mail.Read offline_access"

_ca_bundle = "/root/.ccr/ca-bundle.crt"
_ctx = ssl.create_default_context(cafile=_ca_bundle if os.path.exists(_ca_bundle) else None)
_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
_handlers = [urllib.request.HTTPSHandler(context=_ctx)]
if _proxy:
    _handlers.append(urllib.request.ProxyHandler({"https": _proxy, "http": _proxy}))
_opener = urllib.request.build_opener(*_handlers)


def post(url: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with _opener.open(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        return json.load(e)


def main():
    client_id = os.environ.get("MS_CLIENT_ID")
    tenant_id = os.environ.get("MS_TENANT_ID")
    if not client_id or not tenant_id:
        print("Missing MS_CLIENT_ID or MS_TENANT_ID env vars", file=sys.stderr)
        sys.exit(1)

    devicecode_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    resp = post(devicecode_url, {"client_id": client_id, "scope": SCOPES})
    if "error" in resp:
        print(json.dumps(resp, indent=2), file=sys.stderr)
        sys.exit(1)

    print(resp["message"])
    print("\nĐang chờ bạn đăng nhập...")

    interval = resp.get("interval", 5)
    device_code = resp["device_code"]
    expires_at = time.time() + resp.get("expires_in", 900)

    while time.time() < expires_at:
        time.sleep(interval)
        try:
            token_resp = post(token_url, {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": client_id,
                "device_code": device_code,
            })
        except urllib.error.URLError as e:
            print(f"(mạng gián đoạn, thử lại: {e})", file=sys.stderr)
            continue
        if "error" in token_resp:
            if token_resp["error"] == "authorization_pending":
                continue
            print(json.dumps(token_resp, indent=2), file=sys.stderr)
            sys.exit(1)
        print("\nThành công! Lưu giá trị dưới đây làm MS_REFRESH_TOKEN (không commit vào repo):\n")
        print(token_resp["refresh_token"])
        return

    print("Hết thời gian chờ đăng nhập.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
