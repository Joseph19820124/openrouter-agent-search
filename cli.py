import argparse
import json
import os
import sys

import requests


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="search-web",
        description="Search OpenAI websites through the FastAPI backend.",
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "-n",
        "--num",
        type=int,
        default=5,
        help="Maximum number of results to request",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON instead of formatted text",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    api_base = os.environ.get("BACKEND_API_BASE", "http://127.0.0.1:8000")

    response = requests.post(
        f"{api_base}/agent/search",
        json={"query": args.query, "num": args.num},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    results = payload.get("results", [])
    if not results:
        print("No results found.")
        return 0

    for index, item in enumerate(results, start=1):
        print(f"{index}. {item.get('title', '')}")
        print(item.get("url", ""))
        snippet = item.get("snippet", "")
        if snippet:
            print(snippet)
        if index != len(results):
            print()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        print(detail, file=sys.stderr)
        raise SystemExit(1) from exc
