import argparse
import asyncio
import os
import shlex
import subprocess
from pathlib import Path

import requests
from agents import Agent, Runner, function_tool, set_default_openai_client
from openai import AsyncOpenAI


DEFAULT_API_BASE = "http://127.0.0.1:8000"
DEFAULT_MODEL = "openai/gpt-4.1-mini"
MAX_TOOL_OUTPUT_CHARS = 12000
ALLOWED_SHELL_COMMANDS = {
    "cat",
    "find",
    "git",
    "head",
    "ls",
    "make",
    "node",
    "npm",
    "pnpm",
    "pwd",
    "py.test",
    "pytest",
    "python",
    "python3",
    "rg",
    "sed",
    "tail",
    "uv",
    "wc",
    "yarn",
}

WORKDIR = Path.cwd()


def _truncate(text: str) -> str:
    if len(text) <= MAX_TOOL_OUTPUT_CHARS:
        return text
    return text[:MAX_TOOL_OUTPUT_CHARS] + "\n...[truncated]..."


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = WORKDIR / candidate
    resolved = candidate.resolve()
    if WORKDIR not in resolved.parents and resolved != WORKDIR:
        raise ValueError(f"path escapes workdir: {resolved}")
    return resolved


def _require_llm_env() -> tuple[str, str | None, str]:
    api_key = (
        os.getenv("CODER_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    if not api_key:
        raise SystemExit(
            "Set CODER_API_KEY, OPENROUTER_API_KEY, or OPENAI_API_KEY before running code-agent."
        )

    if os.getenv("CODER_BASE_URL"):
        base_url = os.getenv("CODER_BASE_URL")
    elif os.getenv("CODER_API_KEY"):
        base_url = None
    elif os.getenv("OPENROUTER_API_KEY"):
        base_url = "https://openrouter.ai/api/v1"
    else:
        base_url = None

    model = os.getenv("CODER_MODEL") or os.getenv("OPENROUTER_MODEL") or DEFAULT_MODEL
    return api_key, base_url, model


def _client() -> AsyncOpenAI:
    api_key, base_url, _ = _require_llm_env()
    headers = {}
    if base_url == "https://openrouter.ai/api/v1":
        headers = {
            "HTTP-Referer": os.environ.get("OPENROUTER_SITE_URL", "http://localhost"),
            "X-Title": os.environ.get("OPENROUTER_APP_NAME", "openrouter-agent-search"),
        }
    return AsyncOpenAI(api_key=api_key, base_url=base_url, default_headers=headers)


@function_tool
def list_files(path: str = ".") -> str:
    target = _resolve_path(path)
    if target.is_file():
        return str(target)
    items = sorted(str(p.relative_to(WORKDIR)) for p in target.iterdir())
    return "\n".join(items[:500])


@function_tool
def search_code(query: str, path: str = ".") -> str:
    target = _resolve_path(path)
    cmd = ["rg", "-n", "--hidden", "--glob", "!.git", query, str(target)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=WORKDIR)
    output = result.stdout or result.stderr
    return _truncate(output.strip())


@function_tool
def read_file(path: str, start_line: int = 1, end_line: int = 200) -> str:
    target = _resolve_path(path)
    lines = target.read_text().splitlines()
    start = max(start_line, 1)
    end = min(end_line, len(lines))
    chunk = [
        f"{line_no}: {lines[line_no - 1]}"
        for line_no in range(start, end + 1)
    ]
    return "\n".join(chunk)


@function_tool
def write_file(path: str, content: str) -> str:
    target = _resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"wrote {target}"


@function_tool
def run_shell(command: str) -> str:
    parts = shlex.split(command)
    if not parts:
        raise ValueError("empty command")
    if parts[0] not in ALLOWED_SHELL_COMMANDS:
        raise ValueError(f"command not allowed: {parts[0]}")
    result = subprocess.run(
        parts,
        capture_output=True,
        text=True,
        cwd=WORKDIR,
    )
    output = result.stdout
    if result.stderr:
        output += ("\n" if output else "") + result.stderr
    output = output.strip() or f"exit_code={result.returncode}"
    return _truncate(output)


@function_tool
def web_search(query: str, num: int = 5) -> str:
    api_base = os.getenv("BACKEND_API_BASE", DEFAULT_API_BASE)
    response = requests.post(
        f"{api_base}/agent/search",
        json={"query": query, "num": num},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", [])
    if not results:
        return "No results found."
    lines = []
    for item in results[:num]:
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code-agent",
        description="Minimal coding agent CLI",
    )
    parser.add_argument("task", help="Coding task to execute")
    parser.add_argument(
        "--workdir",
        default=".",
        help="Working directory the agent should operate in",
    )
    return parser


async def run_task(task: str) -> str:
    _, _, model = _require_llm_env()
    set_default_openai_client(_client())
    agent = Agent(
        name="Coding Agent",
        model=model,
        instructions=(
            "You are a pragmatic coding agent. "
            "Use the available tools to inspect the repository, make targeted edits, "
            "and verify what you changed. "
            "Prefer search_code and read_file before write_file. "
            "Use run_shell for safe repo inspection or tests. "
            "Keep final answers concise and mention edited files."
        ),
        tools=[
            list_files,
            search_code,
            read_file,
            write_file,
            run_shell,
            web_search,
        ],
    )
    result = await Runner.run(agent, task)
    return str(result.final_output)


def main() -> int:
    global WORKDIR
    args = build_parser().parse_args()
    WORKDIR = _resolve_path(args.workdir)
    os.chdir(WORKDIR)
    print(asyncio.run(run_task(args.task)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
