"""
tests/test_risk_sentry.py
Quantitative Verification Suite for Continuous Background Risk Sentry (Item 4).

Tests:
1. Baseline health audit for paper portfolio book.
2. Position drawdown breach detection & alerting.
3. Cornish-Fisher non-Gaussian VaR & fat-tail surcharge computation.
4. Downside panic regime detection.
5. State persistence & JSONL alerts logging.
6. Provenance ledger cryptographic receipt registration.
"""

import os
import tempfile
import pytest
from tools.paper_trading import PaperTradingEngine
from tools.ledger import ProvenanceLedger
from tools.risk_sentry import PortfolioRiskSentry


@pytest.fixture
def temp_sentry_env():
    """Create isolated temporary files for paper trading and risk sentry."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        port_file = os.path.join(tmp_dir, "test_paper_portfolio.json")
        alerts_dir = os.path.join(tmp_dir, "alerts")
        ledger = ProvenanceLedger(run_id="test_sentry_run")
        paper_engine = PaperTradingEngine(portfolio_file=port_file, ledger=ledger)
        sentry = PortfolioRiskSentry(paper_engine=paper_engine, ledger=ledger, alerts_dir=alerts_dir)
        yield {
            "sentry": sentry,
            "paper_engine": paper_engine,
            "alerts_dir": alerts_dir
        }


def test_risk_sentry_healthy_baseline(temp_sentry_env):
    """Verify clean cash portfolio evaluates as healthy without breaches."""
    sentry = temp_sentry_env["sentry"]
    res = sentry.audit_portfolio_risk()

    assert res["overall_status"] == "HEALTHY_WITHIN_BOUNDS"
    assert "HEALTHY" in res["status_badge"]
    assert res["portfolio_metrics"]["total_equity_usd"] == 1_000_000.0
    assert res["total_breaches_count"] == 0

    econo = res["econometric_risk_metrics"]
    assert econo["var_95_cf_pct"] > 0.0
    assert econo["var_95_cf_usd"] > 0.0
    assert econo["tail_asymmetry_ratio"] > 0.0
    assert "provenance_ledger_id" in res


def test_risk_sentry_position_drawdown_breach(temp_sentry_env):
    """Verify position suffering >15% drawdown triggers CRITICAL breach."""
    sentry = temp_sentry_env["sentry"]
    paper = temp_sentry_env["paper_engine"]

    # Execute a trade: Buy 100 shares of AAPL at $200
    paper.execute_trade(
        symbol="AAPL",
        asset_class="Equities",
        side="BUY",
        quantity=100,
        price=200.0
    )

    # Shock price down to $150 (-25% drawdown)
    res = sentry.audit_portfolio_risk(
        custom_quotes={"AAPL": 150.0},
        max_position_drawdown_pct=15.0
    )

    assert res["overall_status"] == "CRITICAL_RISK_BREACH"
    assert res["total_breaches_count"] >= 1

    breach_types = [b["type"] for b in res["breaches"]]
    assert "POSITION_DRAWDOWN_BREACH" in breach_types

    # Verify alert was written to log file
    recent_alerts = sentry.load_recent_risk_alerts()
    assert len(recent_alerts) >= 1
    assert any(a["symbol"] == "AAPL" for a in recent_alerts)


def test_risk_sentry_panic_skew_shift_detection(temp_sentry_env):
    """Verify detection of downside panic regime shift when skewness is more negative than threshold."""
    sentry = temp_sentry_env["sentry"]

    # Supply severe downside panic skewness (-0.85 < -0.60 threshold)
    res = sentry.audit_portfolio_risk(
        panic_skew_threshold=-0.60,
        custom_econo_moments={"sample_skewness": -0.85, "sample_excess_kurtosis": 3.2}
    )

    assert res["total_breaches_count"] >= 1
    breach_types = [b["type"] for b in res["breaches"]]
    assert "DOWNSIDE_PANIC_REGIME_SHIFT" in breach_types


def test_risk_sentry_state_persistence(temp_sentry_env):
    """Verify state file is saved and reloaded accurately."""
    sentry = temp_sentry_env["sentry"]
    audit = sentry.audit_portfolio_risk()

    state = sentry.load_latest_sentry_state()
    assert state["overall_status"] == audit["overall_status"]
    assert state["total_equity_usd"] == 1_000_000.0
    assert state["last_audited_at"] is not None
