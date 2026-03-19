import json
import os
from urllib.parse import urlencode

import urllib3


http = urllib3.PoolManager()

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
GOOGLE_CSE_ID = os.environ["GOOGLE_CSE_ID"]


def google_search(query: str, num: int = 5, start: int = 1) -> dict:
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "num": max(1, min(num, 10)),
        "start": max(1, start),
    }

    url = f"https://www.googleapis.com/customsearch/v1?{urlencode(params)}"
    resp = http.request("GET", url, timeout=urllib3.Timeout(connect=5.0, read=20.0))
    body = resp.data.decode("utf-8")

    if resp.status != 200:
        raise RuntimeError(f"Google search failed: status={resp.status}, body={body}")

    raw = json.loads(body)
    items = raw.get("items", [])

    results = []
    for item in items:
        results.append(
            {
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("snippet"),
                "displayLink": item.get("displayLink"),
            }
        )

    return {
        "query": query,
        "results": results,
        "searchInformation": raw.get("searchInformation", {}),
    }


def handler(event, context):
    try:
        if isinstance(event, str):
            event = json.loads(event)

        query = (event or {}).get("query", "").strip()
        num = int((event or {}).get("num", 5))

        if not query:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing 'query'"}),
                "headers": {"Content-Type": "application/json"},
            }

        payload = google_search(query=query, num=num)

        return {
            "statusCode": 200,
            "body": json.dumps(payload),
            "headers": {"Content-Type": "application/json"},
        }
    except Exception as exc:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(exc)}),
            "headers": {"Content-Type": "application/json"},
        }
