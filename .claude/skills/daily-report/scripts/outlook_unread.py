#!/usr/bin/env python3
"""Fetch unread Outlook messages via Microsoft Graph API.

Credentials are read from environment variables only:
  MS_CLIENT_ID, MS_CLIENT_SECRET, MS_TENANT_ID, MS_REFRESH_TOKEN

Prints a JSON list of {"from": str, "subject": str, "preview": str, "received": str}.
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
import urllib.parse

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

_ca_bundle = "/root/.ccr/ca-bundle.crt"
_ctx = ssl.create_default_context(cafile=_ca_bundle if os.path.exists(_ca_bundle) else None)
_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
_handlers = [urllib.request.HTTPSHandler(context=_ctx)]
if _proxy:
    _handlers.append(urllib.request.ProxyHandler({"https": _proxy, "http": _proxy}))
_opener = urllib.request.build_opener(*_handlers)


def get_access_token() -> str:
    tenant_id = os.environ["MS_TENANT_ID"]
    data = urllib.parse.urlencode({
        "client_id": os.environ["MS_CLIENT_ID"],
        "client_secret": os.environ["MS_CLIENT_SECRET"],
        "refresh_token": os.environ["MS_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
        "scope": "https://graph.microsoft.com/.default offline_access",
    }).encode()
    req = urllib.request.Request(
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        data=data,
        method="POST",
    )
    with _opener.open(req) as resp:
        return json.load(resp)["access_token"]


def fetch_unread(token: str, hours: int = 24):
    filter_query = "isRead eq false"
    params = urllib.parse.urlencode({
        "$filter": filter_query,
        "$top": "25",
        "$select": "from,subject,bodyPreview,receivedDateTime",
        "$orderby": "receivedDateTime desc",
    })
    req = urllib.request.Request(
        f"{GRAPH_BASE}/me/mailFolders/inbox/messages?{params}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with _opener.open(req) as resp:
        payload = json.load(resp)
    results = []
    for msg in payload.get("value", []):
        sender = msg.get("from", {}).get("emailAddress", {})
        results.append({
            "from": sender.get("address", "unknown"),
            "subject": msg.get("subject", ""),
            "preview": msg.get("bodyPreview", ""),
            "received": msg.get("receivedDateTime", ""),
        })
    return results


def main():
    required = ["MS_CLIENT_ID", "MS_CLIENT_SECRET", "MS_TENANT_ID", "MS_REFRESH_TOKEN"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(json.dumps({"error": f"missing env vars: {', '.join(missing)}"}))
        sys.exit(1)

    token = get_access_token()
    messages = fetch_unread(token)
    print(json.dumps(messages, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
