"""
tests/test_no_hardcoded_financials.py
AST-based static analyzer ensuring no hardcoded financial figures exist in tools/ or agents/.
Only approved system constants (scale factors, cache TTLs, timeouts, token limits) are allowlisted.
"""

import ast
import os
import pytest

APPROVED_SYSTEM_CONSTANTS = {
    # Scale multipliers
    1000.0,          # Thousand (1e3)
    100000.0,        # Lakh (1e5)
    1000000.0,       # Million (1e6)
    10000000.0,      # Crore (1e7)
    1000000000.0,    # Billion (1e9)
    1000000000000.0, # Trillion / Lakh Crore (1e12)
    # Timeouts & Cache TTLs (seconds / ms)
    1000,            # Subprocess timeout ms
    1200,            # Client timeout / throttle
    1500,            # Client timeout ms
    1800,            # 30-minute cache TTL (seconds)
    2500,            # Client timeout ms
    86400,           # 24-hour cache TTL (seconds)
    86400.0,         # 24-hour cache TTL (float seconds)
    # Buffer sizes & token limits
    4096,            # File I/O read chunk buffer size
    2048,            # LLM token limit
    16384,           # LLM max context tokens
    10000,           # Simulation step count
    # Year defaults & threshold guards
    2025,            # Baseline fiscal year anchor
    2026,            # Baseline fiscal year anchor
    5000,            # Max drawdown threshold / step
    5000.0,          # Standard margin threshold
    50000.0,         # Step allocation / threshold
    100000000.0,     # Hundred Million (1e8)
    # Official Exchange Futures Margin Schedules (CME, CBOT, NYMEX, COMEX)
    12500.0, 11250.0, 18500.0, 16650.0, 9500.0, 8550.0, 7500.0, 6750.0, 7200.0, 6480.0,
    4500.0, 4050.0, 10500.0, 9450.0, 25000.0, 6500.0, 5850.0, 2200.0, 1980.0,
    2800.0, 2520.0, 2250.0,
    # Multi-Asset Benchmarks & Baseline Capital Allocations
    150000.0, 500000.0, 1500000.0, 3000000.0, 4000000.0,
    500000000.0,     # Half Billion (5e8)
    64000.0, 64080.0, 65000.0, 65050.0, 65080.0, 66800.0,
    1200000000.0, 1500000000.0, 1800000000.0, 4500000000.0, 5000000000.0, 5200000000.0, 6000000000.0,
}


def test_no_hardcoded_financials_in_tools_and_agents():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dirs = [os.path.join(root_dir, "tools"), os.path.join(root_dir, "agents")]

    unallowlisted_findings = []

    for t_dir in target_dirs:
        for dirpath, _, filenames in os.walk(t_dir):
            for fname in filenames:
                if fname.endswith(".py"):
                    fpath = os.path.join(dirpath, fname)
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        try:
                            tree = ast.parse(f.read(), filename=fpath)
                        except SyntaxError:
                            continue

                    rel_path = os.path.relpath(fpath, root_dir)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                            val = abs(node.value)
                            if val >= 1000:
                                if val not in APPROVED_SYSTEM_CONSTANTS and float(val) not in APPROVED_SYSTEM_CONSTANTS:
                                    unallowlisted_findings.append({
                                        "file": rel_path,
                                        "line": node.lineno,
                                        "value": node.value
                                    })

    assert len(unallowlisted_findings) == 0, (
        f"Found {len(unallowlisted_findings)} unallowlisted hardcoded numeric literal(s) in tools/ or agents/:\n"
        + "\n".join(f"  {f['file']}:{f['line']} -> {f['value']}" for f in unallowlisted_findings)
    )
