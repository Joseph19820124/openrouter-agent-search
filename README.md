# OpenRouter Agent Search

Minimal reference project for:

- OpenRouter as the LLM provider
- OpenAI Agents SDK for orchestration
- FastAPI as the tool backend
- Vertex AI Search for website search

## Architecture

```text
Agent SDK
  -> custom function tool: search_web()
  -> FastAPI /agent/search
  -> Vertex AI Search
  -> results returned to the agent
```

## Files

- `agent_app.py`: Agent SDK app wired to OpenRouter
- `backend_api.py`: FastAPI backend that calls Vertex AI Search
- `lambda/lambda_function.py`: Legacy Lambda example for Google Custom Search

## Prerequisites

- Python 3.10+
- An OpenRouter API key
- A GCP project with Vertex AI Search / Discovery Engine enabled
- A Google service account JSON key with Vertex AI Search access

Google docs:

- https://docs.cloud.google.com/generative-ai-app-builder/docs/create-engine-es
- https://docs.cloud.google.com/generative-ai-app-builder/docs/create-datastore-ingest

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create an environment file:

```bash
cp .env.example .env
```

Fill in these values in `.env`:

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `VERTEX_PROJECT_ID`
- `VERTEX_ENGINE_ID`
- `GOOGLE_APPLICATION_CREDENTIALS`

Load the environment:

```bash
set -a
source .env
set +a
```

## Run the FastAPI backend

```bash
uvicorn backend_api:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Run the agent

In a second terminal:

```bash
set -a
source .env
set +a
python3 agent_app.py
```

## Vertex AI Search Notes

- This project avoids OpenAI `WebSearchTool` and uses a custom tool instead.
- The backend now calls Vertex AI Search directly and returns a normalized shape:
  - `results[{title,url,snippet}]`
- `VERTEX_ENGINE_ID` should point at a website search app / engine.
- `GOOGLE_APPLICATION_CREDENTIALS` should point at a service account JSON key file on the machine running FastAPI.

## Legacy Path

The `lambda/` directory is kept as a legacy example for the earlier Google Custom Search approach. It is no longer used by the default FastAPI backend.

## Notes

- Using a custom backend still makes it easy to swap the search provider without changing agent logic.
- For OpenRouter, verify the exact model ID in the OpenRouter model catalog before production use.
