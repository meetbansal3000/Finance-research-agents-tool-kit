"""
tests/test_journal_gate.py - Unit Tests for Institutional Journal Gate

Verifies the pre-trade fiduciary invariants:
1. Thesis: Mandatory investment thesis explaining trade rationale.
2. Invalidation Condition: Explicit market condition invalidating the trade.
3. Position Size Rule: Order size must be <= max_position_size_pct of total equity (default 20%).
4. Review Date: Future review date strictly >= today.
5. Audited CSV append to journal/journal.csv and provenance ledger logging.
"""

import os
import tempfile
import datetime
import pytest
from tools.paper_trading import PaperTradingEngine
from tools.journal_gate import JournalGate


@pytest.fixture
def temp_engine_with_gate():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_portfolio = f.name
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f_csv:
        temp_journal_csv = f_csv.name

    if os.path.exists(temp_portfolio):
        os.remove(temp_portfolio)
    if os.path.exists(temp_journal_csv):
        os.remove(temp_journal_csv)

    engine = PaperTradingEngine(
        portfolio_file=temp_portfolio,
        initial_capital=100000.0,
        enforce_journal_gate=True,
        max_position_size_pct=0.20,
        journal_csv_path=temp_journal_csv
    )
    yield engine, temp_journal_csv

    if os.path.exists(temp_portfolio):
        os.remove(temp_portfolio)
    if os.path.exists(temp_journal_csv):
        os.remove(temp_journal_csv)


def test_reject_missing_thesis(temp_engine_with_gate):
    engine, _ = temp_engine_with_gate
    future_date = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()

    ok, msg, data = engine.execute_trade(
        symbol="AAPL",
        asset_class="Equities",
        side="BUY",
        quantity=50.0,
        price=150.0,
        thesis="",  # Missing thesis
        invalidation_condition="Close below 200 EMA",
        review_date=future_date
    )

    assert ok is False
    assert "MISSING_THESIS" in data.get("reason", "")
    assert "Trade thesis is required" in msg


def test_reject_missing_invalidation_condition(temp_engine_with_gate):
    engine, _ = temp_engine_with_gate
    future_date = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()

    ok, msg, data = engine.execute_trade(
        symbol="AAPL",
        asset_class="Equities",
        side="BUY",
        quantity=50.0,
        price=150.0,
        thesis="Strong free cash flow yield with accelerating enterprise services growth",
        invalidation_condition="",  # Missing invalidation
        review_date=future_date
    )

    assert ok is False
    assert "MISSING_INVALIDATION_CONDITION" in data.get("reason", "")
    assert "Invalidation condition is required" in msg


def test_reject_position_size_breach(temp_engine_with_gate):
    engine, _ = temp_engine_with_gate
    future_date = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()

    # Total equity is 100,000. 20% limit = $20,000.
    # Order cost = 200 shares * $150 = $30,000 (30% of equity) -> BREACH!
    ok, msg, data = engine.execute_trade(
        symbol="AAPL",
        asset_class="Equities",
        side="BUY",
        quantity=200.0,
        price=150.0,
        thesis="Strong free cash flow yield with accelerating enterprise services growth",
        invalidation_condition="Close below 200 EMA at $140.00",
        review_date=future_date
    )

    assert ok is False
    assert data.get("reason") == "POSITION_SIZE_BREACH"
    assert "Position size breach" in msg
    assert data["position_size_pct"] == 0.30


def test_dynamic_position_size_rule(temp_engine_with_gate):
    engine, _ = temp_engine_with_gate
    future_date = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()

    # Set strict 10% position limit ($10,000 max)
    engine.set_position_size_rule(0.10)

    # 100 shares * $150 = $15,000 -> Exceeds 10%
    ok, msg, data = engine.execute_trade(
        symbol="AAPL",
        asset_class="Equities",
        side="BUY",
        quantity=100.0,
        price=150.0,
        thesis="Solid momentum breakout above 50-day SMA",
        invalidation_condition="Price rejection back below breakout pivot",
        review_date=future_date
    )
    assert ok is False
    assert data.get("reason") == "POSITION_SIZE_BREACH"

    # 50 shares * $150 = $7,500 -> 7.5% <= 10% -> Passes position size check
    ok, msg, data = engine.execute_trade(
        symbol="AAPL",
        asset_class="Equities",
        side="BUY",
        quantity=50.0,
        price=150.0,
        thesis="Solid momentum breakout above 50-day SMA",
        invalidation_condition="Price rejection back below breakout pivot",
        review_date=future_date
    )
    assert ok is True
    assert "ORDER FILLED" in msg


def test_reject_past_review_date(temp_engine_with_gate):
    engine, _ = temp_engine_with_gate
    past_date = (datetime.date.today() - datetime.timedelta(days=5)).isoformat()

    ok, msg, data = engine.execute_trade(
        symbol="AAPL",
        asset_class="Equities",
        side="BUY",
        quantity=50.0,
        price=150.0,
        thesis="Strong free cash flow yield with accelerating enterprise services growth",
        invalidation_condition="Close below 200 EMA at $140.00",
        review_date=past_date
    )

    assert ok is False
    assert data.get("reason") == "PAST_REVIEW_DATE"
    assert "cannot be in the past" in msg


def test_reject_invalid_review_date_format(temp_engine_with_gate):
    engine, _ = temp_engine_with_gate

    ok, msg, data = engine.execute_trade(
        symbol="AAPL",
        asset_class="Equities",
        side="BUY",
        quantity=50.0,
        price=150.0,
        thesis="Strong free cash flow yield with accelerating enterprise services growth",
        invalidation_condition="Close below 200 EMA at $140.00",
        review_date="not-a-date"
    )

    assert ok is False
    assert data.get("reason") == "INVALID_REVIEW_DATE_FORMAT"


def test_approved_trade_executes_and_records_audit_trail(temp_engine_with_gate):
    engine, temp_journal_csv = temp_engine_with_gate
    future_date = (datetime.date.today() + datetime.timedelta(days=45)).isoformat()
    thesis_text = "Compelling DCF margin of safety: FCF yield > 7% with low cyclicality"
    invalidation_text = "Trailing twelve-month operating margin falling below 18%"

    # 100 shares @ $120 = $12,000 (12% of $100k equity <= 20% rule)
    ok, msg, pos = engine.execute_trade(
        symbol="MSFT",
        asset_class="Equities",
        side="BUY",
        quantity=100.0,
        price=120.0,
        thesis=thesis_text,
        invalidation_condition=invalidation_text,
        review_date=future_date
    )

    assert ok is True
    assert "ORDER FILLED" in msg
    assert pos["symbol"] == "MSFT"
    assert pos["thesis"] == thesis_text
    assert pos["invalidation_condition"] == invalidation_text
    assert pos["review_date"] == future_date
    assert pos["journal_gate"]["status"] == "PASSED"

    # Check portfolio state
    portfolio = engine.load_portfolio()
    saved_pos = portfolio["positions"][0]
    assert saved_pos["thesis"] == thesis_text
    assert saved_pos["invalidation_condition"] == invalidation_text
    assert saved_pos["review_date"] == future_date


def test_append_journal_csv_record(tmp_path):
    csv_file = tmp_path / "journal.csv"
    success = JournalGate.append_journal_record(
        order_id="ORD-TEST-101",
        symbol="NVDA",
        side="BUY",
        entry_price=125.50,
        quantity=50.0,
        thesis="Blackwell ramp margin acceleration",
        invalidation_condition="Data center capex deceleration below 15% YoY",
        review_date="2026-11-30",
        journal_csv_path=str(csv_file)
    )

    assert success is True
    assert csv_file.exists()
    content = csv_file.read_text(encoding="utf-8")
    assert "ORD-TEST-101" in content
    assert "NVDA" in content
    assert "Blackwell ramp margin acceleration" in content
    assert "Data center capex deceleration below 15% YoY" in content
    assert "Reviewed on 2026-11-30" in content
