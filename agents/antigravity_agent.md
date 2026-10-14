# Antigravity Finance Agent (`agents/antigravity_agent.md`)

## Role & Mission
The Antigravity Finance Agent is an autonomous, stateful market intelligence and investment research agent powered by the **Google Antigravity SDK (`google-antigravity`)** and **Google Gemini**.

It connects the research toolkit's data layer, filing parser, and provenance ledger with Gemini's high-context reasoning and Antigravity's stateful conversation framework.

## Capabilities
1. **Interactive & Autonomous Research**: Operates in multi-turn interactive mode (`AgentBehavior.INTERACTIVE`) with state persistence via `ToolContext` or single-shot autonomous mode (`AgentBehavior.AUTONOMOUS`).
2. **Tool-First Quantitative Grounding**: Calls native financial tools (`get_stock_quote`, `get_financial_metrics`, `get_historical_performance`, `manage_portfolio`, `get_company_news`, and research toolkit data layers).
3. **Structured Reporting & Verification**: Produces structured markdown reports complete with balance sheet indicators, valuation multiples, and risk matrices.
4. **Local Harness & Sandboxing**: Executes on the local machine with safety policies managed by Antigravity's local harness.
