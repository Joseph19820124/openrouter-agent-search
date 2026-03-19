import json
import os

import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI()

lambda_client = boto3.client(
    "lambda",
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

SEARCH_LAMBDA_NAME = os.environ["SEARCH_LAMBDA_NAME"]


class SearchRequest(BaseModel):
    query: str
    num: int = 5


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/agent/search")
def agent_search(req: SearchRequest) -> dict:
    try:
        response = lambda_client.invoke(
            FunctionName=SEARCH_LAMBDA_NAME,
            InvocationType="RequestResponse",
            Payload=json.dumps(
                {"query": req.query, "num": req.num}
            ).encode("utf-8"),
        )

        raw = response["Payload"].read().decode("utf-8")
        payload = json.loads(raw)

        if "body" in payload and isinstance(payload["body"], str):
            payload = json.loads(payload["body"])

        return payload
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
