import asyncio
import os

import requests
from agents import Agent, Runner, function_tool, set_default_openai_client
from openai import AsyncOpenAI


client = AsyncOpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": os.environ.get("OPENROUTER_SITE_URL", "http://localhost"),
        "X-Title": os.environ.get("OPENROUTER_APP_NAME", "openrouter-agent-search"),
    },
)

set_default_openai_client(client)

API_BASE = os.environ.get("BACKEND_API_BASE", "http://127.0.0.1:8000")


@function_tool
def search_web(query: str) -> str:
    resp = requests.post(
        f"{API_BASE}/agent/search",
        json={"query": query, "num": 5},
        timeout=30,
    )
    resp.raise_for_status()

    payload = resp.json()
    results = payload.get("results", [])
    if not results:
        return "No results found."

    lines = []
    for item in results[:5]:
        lines.append(
            "\n".join(
                [
                    f"Title: {item.get('title', '')}",
                    f"URL: {item.get('url', '')}",
                    f"Snippet: {item.get('snippet', '')}",
                ]
            )
        )
    return "\n\n".join(lines)


async def main() -> None:
    agent = Agent(
        name="Research Assistant",
        instructions=(
            "You are a concise research assistant. "
            "Use search_web for fresh or factual lookups. "
            "Answer in Chinese. "
            "Always include source URLs in the final answer."
        ),
        model=os.environ.get("OPENROUTER_MODEL", "openai/gpt-4.1-mini"),
        tools=[search_web],
    )

    prompt = os.environ.get(
        "AGENT_PROMPT",
        "查一下 OpenAI Responses API 是什么，并给我两句总结和来源链接。",
    )
    result = await Runner.run(agent, prompt)
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
