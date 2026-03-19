# OpenRouter Agent Search

Minimal reference project for:

- OpenRouter as the LLM provider
- OpenAI Agents SDK for orchestration
- FastAPI as the tool backend
- AWS Lambda for Google Custom Search JSON API calls

## Architecture

```text
Agent SDK
  -> custom function tool: search_web()
  -> FastAPI /agent/search
  -> AWS Lambda
  -> Google Custom Search JSON API
  -> results returned to the agent
```

## Files

- `agent_app.py`: Agent SDK app wired to OpenRouter
- `backend_api.py`: FastAPI backend that invokes Lambda
- `lambda/lambda_function.py`: Lambda function that calls Google Custom Search

## Prerequisites

- Python 3.10+
- An OpenRouter API key
- An AWS account with Lambda access
- A Google Programmable Search Engine
- A Google Custom Search JSON API key

Google docs:

- https://developers.google.com/custom-search/v1/overview
- https://developers.google.com/custom-search/v1/using_rest

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
- `SEARCH_LAMBDA_NAME`
- `GOOGLE_API_KEY`
- `GOOGLE_CSE_ID`

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

## Deploy the Lambda

Install the Lambda dependency into a build folder:

```bash
cd lambda
python3 -m pip install -r requirements.txt -t package
cp lambda_function.py package/
cd package
zip -r ../lambda.zip .
```

Upload `lambda/lambda.zip` to AWS Lambda and set these environment variables on the function:

- `GOOGLE_API_KEY`
- `GOOGLE_CSE_ID`

The Lambda handler should be:

```text
lambda_function.handler
```

## Notes

- This project avoids OpenAI `WebSearchTool` and uses a custom tool instead.
- That makes it easier to swap the search backend without changing the agent logic.
- For OpenRouter, verify the exact model ID in the OpenRouter model catalog before production use.
