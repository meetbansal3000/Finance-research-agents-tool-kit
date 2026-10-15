"""
connectors - External AI Integration Suite
Exposes the Meridian Financial Workstation to Claude, Groq, Cursor, Codex, and OpenAI.
"""

from connectors.mcp_server import (
    MCP_TOOLS,
    dispatch_tool,
    run_mcp_server
)
from connectors.groq_connector import (
    FINANCIAL_TOOLS_SCHEMA,
    execute_tool_call,
    run_groq_agent
)

__all__ = [
    "MCP_TOOLS",
    "FINANCIAL_TOOLS_SCHEMA",
    "dispatch_tool",
    "execute_tool_call",
    "run_mcp_server",
    "run_groq_agent"
]
