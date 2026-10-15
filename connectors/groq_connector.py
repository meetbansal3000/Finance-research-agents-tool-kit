"""
connectors/groq_connector.py - Groq & OpenAI Function Calling Connector
Universal OpenAI/Groq tool-calling connector exposing Meridian's 10 Quantitative Desks,
Probability Simulator, and $1,000,000 Paper Trading Engine to Groq (Llama 3.3 70B, etc.),
OpenAI (GPT-4o, etc.), and custom agent loops.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from connectors.mcp_server import dispatch_tool, MCP_TOOLS


# =============================================================================
# OPENAI / GROQ FUNCTION CALLING TOOLS SCHEMA
# =============================================================================

def _convert_mcp_to_openai_schema(mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Converts MCP tool definitions to standard OpenAI / Groq function-calling schemas."""
    schemas = []
    for tool in mcp_tools:
        schemas.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["inputSchema"]
            }
        })
    return schemas


FINANCIAL_TOOLS_SCHEMA: List[Dict[str, Any]] = _convert_mcp_to_openai_schema(MCP_TOOLS)


# =============================================================================
# TOOL EXECUTION DISPATCHER
# =============================================================================

def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Directly dispatches an OpenAI/Groq tool call to Meridian's quantitative backends.
    Returns JSON-serializable dictionary.
    """
    try:
        return dispatch_tool(tool_name, arguments)
    except Exception as e:
        return {
            "error": str(e),
            "tool": tool_name,
            "status": "FAILED"
        }


# =============================================================================
# MULTI-TURN GROQ / OPENAI AGENT RUNNER
# =============================================================================

SYSTEM_PROMPT = """You are Meridian Financial Research Assistant, an institutional AI quantitative workstation powered by 5 specialized trading desks:
1. Options Greek Strategist (Black-Scholes analytical Greeks, multi-leg payoff curves)
2. Futures & Commodity Desk (CME term structure, contango/backwardation, roll yields)
3. Fixed Income Macro Desk (Treasury yield curve, inversion alerts, credit spreads)
4. Crypto & 24/7 Derivatives Desk (Perpetual funding rates, liquidation risk)
5. Cross-Asset Risk Officer (Cornish-Fisher VaR/CVaR, crisis stress testing)
6. Live Market Paper Trading Desk ($1,000,000 simulation portfolio mirroring live real-world pricing)

Always use the provided tools to fetch live quotes, resolve companies to tickers, calculate Greeks, simulate econometric probabilities, and execute paper trades. Never fabricate financial figures or return static guesses."""


def run_groq_agent(
    prompt: str,
    api_key: Optional[str] = None,
    model: str = "llama-3.3-70b-versatile",
    max_turns: int = 5,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Executes a complete multi-turn conversational agent loop using Groq with tool calling.
    If 'groq' package is not installed or API key is not set, runs in simulated offline mode.
    """
    groq_key = api_key or os.environ.get("GROQ_API_KEY")

    if not groq_key:
        if verbose:
            print("[Groq Connector] Note: GROQ_API_KEY not set. Running in offline tool-dispatch mode.")
        
        # Offline intelligent parsing: check if prompt mentions symbols or common actions
        simulated_tools_called = []
        lower_p = prompt.lower()

        # Heuristic test dispatch
        if any(w in lower_p for w in ["micron", "mu", "apple", "aapl", "nvidia", "nvda", "tesla", "tsla"]):
            # Extract possible query
            target = "MU" if "micron" in lower_p or "mu" in lower_p else "AAPL"
            if "nvda" in lower_p or "nvidia" in lower_p:
                target = "NVDA"
            elif "tesla" in lower_p or "tsla" in lower_p:
                target = "TSLA"
            
            res_resolve = execute_tool_call("resolve_ticker", {"query": target})
            simulated_tools_called.append({"tool": "resolve_ticker", "args": {"query": target}, "output": res_resolve})

            if "quote" in lower_p or "price" in lower_p:
                res_quote = execute_tool_call("get_live_quote", {"symbol": res_resolve.get("symbol", target)})
                simulated_tools_called.append({"tool": "get_live_quote", "args": {"symbol": target}, "output": res_quote})

            if "greek" in lower_p or "option" in lower_p:
                spot = res_resolve.get("price", 100.0)
                atm_k = res_resolve.get("atm_strike", spot)
                iv = res_resolve.get("atm_iv_pct", 35.0) / 100.0
                res_greeks = execute_tool_call("calculate_options_greeks", {
                    "spot": spot, "strike": atm_k, "dte": 30, "iv": iv, "r": 0.045, "option_type": "call"
                })
                simulated_tools_called.append({"tool": "calculate_options_greeks", "args": {"spot": spot, "strike": atm_k}, "output": res_greeks})

        elif "portfolio" in lower_p or "paper" in lower_p or "cash" in lower_p:
            res_port = execute_tool_call("get_paper_portfolio", {})
            simulated_tools_called.append({"tool": "get_paper_portfolio", "args": {}, "output": res_port})

        elif "simulate" in lower_p or "probability" in lower_p:
            res_sim = execute_tool_call("simulate_econometric_probability", {
                "mode": "single_stock", "spot": 100.0, "target_price": 110.0, "dte": 30, "volatility": 0.25
            })
            simulated_tools_called.append({"tool": "simulate_econometric_probability", "args": {"mode": "single_stock"}, "output": res_sim})

        return {
            "mode": "offline_dispatch",
            "prompt": prompt,
            "tool_calls_executed": simulated_tools_called,
            "final_response": f"Executed {len(simulated_tools_called)} quantitative tool call(s) successfully. Results: {json.dumps(simulated_tools_called, indent=2)}"
        }

    try:
        from groq import Groq
    except ImportError:
        return {
            "error": "The 'groq' python library is not installed. Install via: pip install groq",
            "status": "MISSING_DEPENDENCY"
        }

    client = Groq(api_key=groq_key)
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    executed_calls = []

    for turn in range(max_turns):
        if verbose:
            print(f"[Groq Agent] Turn {turn + 1}: querying model {model}...")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=FINANCIAL_TOOLS_SCHEMA,
            tool_choice="auto",
            temperature=0.2
        )

        choice = response.choices[0]
        msg = choice.message

        # Append assistant message to history
        messages.append(msg)

        if not msg.tool_calls:
            # Model has generated final natural language response
            if verbose:
                print(f"[Groq Agent] Final response reached after {turn + 1} turn(s).")
            return {
                "prompt": prompt,
                "turns_taken": turn + 1,
                "tool_calls_executed": executed_calls,
                "final_response": msg.content
            }

        # Dispatch each tool call
        for t_call in msg.tool_calls:
            fn_name = t_call.function.name
            raw_args = t_call.function.arguments
            try:
                fn_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except Exception:
                fn_args = {}

            if verbose:
                print(f"[Groq Agent] Tool Call -> {fn_name}({json.dumps(fn_args)})")

            result = execute_tool_call(fn_name, fn_args)
            executed_calls.append({
                "id": t_call.id,
                "name": fn_name,
                "arguments": fn_args,
                "result": result
            })

            # Append tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": t_call.id,
                "name": fn_name,
                "content": json.dumps(result)
            })

    return {
        "prompt": prompt,
        "turns_taken": max_turns,
        "tool_calls_executed": executed_calls,
        "final_response": "Reached maximum turns without completion."
    }


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Groq / OpenAI Financial Workstation Connector")
    parser.add_argument("--prompt", type=str, required=True, help="User query for the financial assistant")
    parser.add_argument("--model", type=str, default="llama-3.3-70b-versatile", help="Groq model ID")
    parser.add_argument("--api-key", type=str, default=None, help="Groq API Key (or set GROQ_API_KEY env)")
    parser.add_argument("--schema-only", action="store_true", help="Print tool definitions schema and exit")

    args = parser.parse_args()

    if args.schema_only:
        print(json.dumps(FINANCIAL_TOOLS_SCHEMA, indent=2))
        return

    res = run_groq_agent(
        prompt=args.prompt,
        api_key=args.api_key,
        model=args.model,
        verbose=True
    )
    print("\n--- AGENT RESULT ---")
    print(res.get("final_response"))


if __name__ == "__main__":
    main()
