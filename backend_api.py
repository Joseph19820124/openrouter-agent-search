import os

import requests
from fastapi import FastAPI, HTTPException
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from pydantic import BaseModel


app = FastAPI()

VERTEX_PROJECT_ID = os.environ["VERTEX_PROJECT_ID"]
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "global")
VERTEX_COLLECTION = os.getenv("VERTEX_COLLECTION", "default_collection")
VERTEX_ENGINE_ID = os.environ["VERTEX_ENGINE_ID"]
GOOGLE_APPLICATION_CREDENTIALS = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
VERTEX_SEARCH_PAGE_SIZE = int(os.getenv("VERTEX_SEARCH_PAGE_SIZE", "5"))
VERTEX_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


class SearchRequest(BaseModel):
    query: str
    num: int = 5


def _vertex_search_url() -> str:
    return (
        "https://discoveryengine.googleapis.com/v1/"
        f"projects/{VERTEX_PROJECT_ID}/locations/{VERTEX_LOCATION}/"
        f"collections/{VERTEX_COLLECTION}/engines/{VERTEX_ENGINE_ID}/"
        "servingConfigs/default_search:search"
    )


def _google_access_token() -> str:
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_APPLICATION_CREDENTIALS,
        scopes=[VERTEX_SCOPE],
    )
    credentials.refresh(Request())
    return credentials.token


def _normalize_results(payload: dict) -> dict:
    results = []
    for item in payload.get("results", []):
        derived = item.get("document", {}).get("derivedStructData", {})
        snippets = derived.get("snippets", [])
        snippet = snippets[0].get("snippet", "") if snippets else ""
        results.append(
            {
                "title": derived.get("title", ""),
                "url": derived.get("link", ""),
                "snippet": snippet,
            }
        )

    return {
        "results": results,
        "totalSize": payload.get("totalSize"),
        "nextPageToken": payload.get("nextPageToken", ""),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/agent/search")
def agent_search(req: SearchRequest) -> dict:
    try:
        token = _google_access_token()
        response = requests.post(
            _vertex_search_url(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Goog-User-Project": VERTEX_PROJECT_ID,
            },
            json={
                "query": req.query,
                "pageSize": min(req.num, VERTEX_SEARCH_PAGE_SIZE),
            },
            timeout=30,
        )
        response.raise_for_status()
        return _normalize_results(response.json())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
