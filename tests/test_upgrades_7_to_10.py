"""
tests/test_upgrades_7_to_10.py
Comprehensive unit test suite for:
  - Upgrade 7: Filing & event alerts monitor (tools/alerts.py)
  - Upgrade 8: Scheduled weekly briefing Workflow 10 (tools/briefing.py)
  - Upgrade 9: Investment decision journal (tools/journal.py)
  - Upgrade 10: Quantitative backtesting and screening sandbox (tools/backtest.py)
"""

import os
import shutil
import pytest
from tools.alerts import AlertMonitor
from tools.briefing import WeeklyBriefingGenerator
from tools.journal import DecisionJournal
from tools.backtest import BacktestSandbox


@pytest.fixture
def temp_dir(tmp_path):
    d = tmp_path / "test_finance_env"
    d.mkdir()
    return str(d)


def test_alert_monitor(temp_dir):
    """Test Upgrade 7 AlertMonitor state, watchlist loading, and alert logging."""
    monitor = AlertMonitor(alerts_dir=temp_dir)
    tickers = monitor.load_watchlist_tickers()
    assert len(tickers) >= 1
    assert "AAPL" in tickers or "GOOGL" in tickers

    # Test state persistence
    monitor.state["seen_accessions"].append("TEST_ACC_001")
    monitor._save_state()
    reloaded = monitor._load_state()
    assert "TEST_ACC_001" in reloaded["seen_accessions"]

    # Test markdown report rendering
    sample_alerts = [
        {
            "alert_id": "ALERT_TEST_01",
            "ticker": "AAPL",
            "severity": "HIGH",
            "category": "NEW_FILING",
            "title": "New SEC Form 10-K Filed for AAPL",
            "url": "https://www.sec.gov"
        }
    ]
    md = monitor._render_alerts_report(sample_alerts, ["AAPL"])
    assert "Watchlist Event & Filing Alerts Report" in md
    assert "ALERT_TEST_01" not in md  # Table displays title and link
    assert "New SEC Form 10-K Filed for AAPL" in md


def test_weekly_briefing(temp_dir):
    """Test Upgrade 8 WeeklyBriefingGenerator watchlist parsing, macro series, and briefing generation."""
    generator = WeeklyBriefingGenerator()
    assert len(generator.watchlist_items) >= 1

    macro = generator.get_macro_overview()
    assert "US_10Y_Yield" in macro
    assert "Brent_Crude" in macro

    # Test report generation to temp dir
    report_path = generator.generate_briefing(output_dir=temp_dir)
    assert os.path.exists(report_path)
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Weekly Watchlist Research Briefing" in content
    assert "Global Macroeconomic & Financial Barometer" in content
    assert "Watchlist Multi-Timeframe Performance" in content


def test_decision_journal(temp_dir):
    """Test Upgrade 9 DecisionJournal logging, closure, post-mortem, and portfolio summary."""
    journal = DecisionJournal(journal_dir=temp_dir)

    # 1. Log a decision
    dec_id = journal.log_decision(
        ticker="GOOGL",
        action="BUY",
        entry_price=300.0,
        target_price=390.0,
        stop_loss=260.0,
        thesis="Dominant advertising moat and AI cloud scale.",
        risks="Antitrust headwinds.",
        conviction="HIGH"
    )
    assert dec_id.startswith("DEC_")
    decisions = journal.list_decisions()
    assert len(decisions) == 1
    assert decisions[0]["ticker"] == "GOOGL"
    assert decisions[0]["status"] == "OPEN"

    # 2. Close decision
    closed = journal.close_decision(
        decision_id=dec_id,
        exit_price=360.0,
        post_mortem_notes="Target reached ahead of schedule with 20% gain."
    )
    assert closed["status"] == "CLOSED"
    assert "+20.00%" in closed["return_pct"]

    # 3. Generate review summary
    rev_path = journal.generate_review_summary()
    assert os.path.exists(rev_path)
    with open(rev_path, "r", encoding="utf-8") as f:
        rev_content = f.read()
    assert "Investment Decision Journal & Portfolio Review" in rev_content
    assert "GOOGL" in rev_content
    assert "+20.00%" in rev_content


def test_backtest_sandbox(temp_dir):
    """Test Upgrade 10 BacktestSandbox fundamental screening and portfolio simulation."""
    sandbox = BacktestSandbox(output_dir=temp_dir)

    # Test fundamental screening
    screen_res = sandbox.screen_universe(
        tickers=["AAPL", "MSFT", "GOOGL"],
        min_op_margin=0.15,
        max_debt_to_equity=3.0,
        min_fcf_yield=0.01
    )
    assert "stats" in screen_res
    assert screen_res["stats"]["initial_universe"] == 3
    assert len(screen_res["results"]) == 3

    # Test portfolio backtest report generation
    dummy_summary = {
        "period": "1y",
        "tickers": ["AAPL", "GOOGL"],
        "benchmark": "SPY",
        "portfolio_return_pct": 18.5,
        "benchmark_return_pct": 15.0,
        "alpha_pct": 3.5,
        "annualized_volatility_pct": 16.2,
        "benchmark_volatility_pct": 14.1,
        "sharpe_ratio": 1.25,
        "max_drawdown_pct": -9.8
    }
    rep_path = os.path.join(temp_dir, "test_backtest.md")
    sandbox._save_backtest_report(rep_path, dummy_summary)
    assert os.path.exists(rep_path)
    with open(rep_path, "r", encoding="utf-8") as f:
        bt_content = f.read()
    assert "Quantitative Backtest Simulation Report" in bt_content
    assert "+18.50%" in bt_content
    assert "+3.50%" in bt_content
