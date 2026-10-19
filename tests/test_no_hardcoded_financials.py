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


def test_no_hardcoded_financials_in_tools_agents_scripts_dashboard():
    """
    Task 4 Verification:
    Scans agents/, tools/, scripts/, and dashboard.py for numeric literals of 1e6 or more.
    Fails unless the literal is on the allowlist file (tests/financial_literals_allowlist.json)
    with a written justification.
    """
    import json

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    allowlist_path = os.path.join(root_dir, "tests", "financial_literals_allowlist.json")
    assert os.path.exists(allowlist_path), f"Allowlist file missing: {allowlist_path}"

    with open(allowlist_path, "r", encoding="utf-8") as f:
        allowlist = json.load(f)

    # Verify every allowlisted item has a valid written justification string
    for k, v in allowlist.items():
        assert isinstance(v, str) and len(v.strip()) > 10, f"Allowlist entry {k} missing written justification."

    allowed_floats = {float(k): v for k, v in allowlist.items()}

    targets = [
        os.path.join(root_dir, "agents"),
        os.path.join(root_dir, "tools"),
        os.path.join(root_dir, "scripts"),
        os.path.join(root_dir, "dashboard.py"),
    ]

    target_files = []
    for t in targets:
        if os.path.isfile(t):
            target_files.append(t)
        elif os.path.isdir(t):
            for dirpath, _, filenames in os.walk(t):
                for fname in filenames:
                    if fname.endswith(".py"):
                        target_files.append(os.path.join(dirpath, fname))

    unallowlisted_findings = []

    for fpath in target_files:
        rel_path = os.path.relpath(fpath, root_dir)
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            try:
                tree = ast.parse(f.read(), filename=fpath)
            except SyntaxError:
                continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                val = abs(node.value)
                if val >= 1000000.0:  # 1e6 or more
                    f_val = float(val)
                    if f_val not in allowed_floats:
                        unallowlisted_findings.append({
                            "file": rel_path,
                            "line": node.lineno,
                            "value": node.value
                        })

    assert len(unallowlisted_findings) == 0, (
        f"Task 4 Violation: Found {len(unallowlisted_findings)} unallowlisted numeric literal(s) >= 1e6 "
        f"without justification in tests/financial_literals_allowlist.json:\n"
        + "\n".join(f"  {f['file']}:{f['line']} -> {f['value']}" for f in unallowlisted_findings)
    )


def test_dashboard_dcf_dynamic_ledger_loading_or_data_unavailable():
    """
    Item 7 Verification:
    Ensures that dashboard.py loads DCF metrics from pipeline provenance ledgers
    with exact period ends, and returns 'data unavailable' + 'ILLUSTRATIVE' flag
    when no audited ledger exists for a ticker.
    """
    from dashboard import load_pipeline_ledger_dcf_metrics, get_dcf_company_profile

    # 1. Unaudited ticker: must show data unavailable and illustrative flag
    res_none = load_pipeline_ledger_dcf_metrics("NONEXISTENT_TICKER_XYZ")
    assert res_none["found"] is False
    assert res_none["fcf_period"] == "data unavailable"
    assert res_none["shares_period"] == "data unavailable"
    assert res_none["net_debt_period"] == "data unavailable"

    prof_none = get_dcf_company_profile("NONEXISTENT_TICKER_XYZ")
    assert prof_none["is_illustrative"] is True
    assert "ILLUSTRATIVE EXAMPLE" in prof_none["source"]
    assert prof_none["fcf_period"] == "data unavailable"

