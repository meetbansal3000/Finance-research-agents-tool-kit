"""Antigravity-powered Financial Intelligence and Research Agent."""

import argparse
import asyncio
import os
import sys
import pathlib

# Ensure workspace root is in sys.path
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from google.antigravity import Agent, LocalAgentConfig, AgentBehavior, types
from tools.antigravity_tools import ANTIGRAVITY_FINANCE_TOOLS

load_dotenv()

SYSTEM_INSTRUCTIONS = """You are the Antigravity Research Analyst in the Open-Source Stock and Market Research Toolkit.

Your mission:
1. Provide accurate, verifiable financial data and quantitative analysis using your integrated tools.
2. Call tools (`get_stock_quote`, `get_historical_performance`, `get_financial_metrics`, `manage_portfolio`) to retrieve actual live metrics. Never guess or hallucinate numbers.
3. Present outputs with clear tables, risk assessments, valuation multiples, and stateful portfolio tracking.
4. Adhere strictly to the workspace guidelines: no direct mental arithmetic, source your figures, and maintain full data transparency.
"""


def build_config(api_key: str | None = None, interactive: bool = True) -> LocalAgentConfig:
    key = api_key or os.environ.get("GEMINI_API_KEY")
    behavior = AgentBehavior.INTERACTIVE if interactive else AgentBehavior.AUTONOMOUS
    
    app_dir = os.environ.get("ANTIGRAVITY_DATA_DIR", os.path.join(PROJECT_ROOT, ".antigravity_data"))
    os.makedirs(app_dir, exist_ok=True)

    kwargs = {
        "tools": ANTIGRAVITY_FINANCE_TOOLS,
        "system_instructions": SYSTEM_INSTRUCTIONS,
        "capabilities": types.CapabilitiesConfig(agent_behavior=behavior),
        "app_data_dir": app_dir,
    }
    if key:
        kwargs["api_key"] = key
    return LocalAgentConfig(**kwargs)


async def run_query(query: str, api_key: str | None = None):
    config = build_config(api_key=api_key, interactive=False)
    print(f"\n[Antigravity Finance Agent] Query: {query}")
    print("-" * 65)
    async with Agent(config) as agent:
        response = await agent.chat(query)
        async for token in response:
            sys.stdout.write(token)
            sys.stdout.flush()
        print("\n")


async def run_interactive(api_key: str | None = None):
    config = build_config(api_key=api_key, interactive=True)
    print("\n" + "=" * 65)
    print("  Antigravity Finance Agent - Research Toolkit")
    print("  Drive D: AI-Workspace | Powered by Google Antigravity SDK")
    print("=" * 65)
    print("  Type your queries or 'exit' to quit.")
    print("=" * 65 + "\n")

    async with Agent(config) as agent:
        while True:
            try:
                user_msg = input("User: ").strip()
                if not user_msg:
                    continue
                if user_msg.lower() in ("exit", "quit", "q"):
                    break
                print("\n[Antigravity]: ", end="", flush=True)
                response = await agent.chat(user_msg)
                async for token in response:
                    sys.stdout.write(token)
                    sys.stdout.flush()
                print("\n")
            except (KeyboardInterrupt, EOFError):
                break


def main():
    parser = argparse.ArgumentParser(description="Antigravity Finance Agent")
    parser.add_argument("--query", "-q", type=str, help="Single research query")
    parser.add_argument("--api-key", "-k", type=str, help="Optional Gemini API key")
    args = parser.parse_args()

    if args.query:
        asyncio.run(run_query(args.query, api_key=args.api_key))
    else:
        asyncio.run(run_interactive(api_key=args.api_key))


if __name__ == "__main__":
    main()
