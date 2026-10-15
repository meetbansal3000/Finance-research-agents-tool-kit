"""
tools/paper_trading.py - Live Paper Trading Execution & Multi-Asset Portfolio Desk
Provides real-deal trade execution mirroring live market prices for:
1. Equities & ETFs (shares, bid/ask fills)
2. Options (calls, puts, multi-leg spreads with x100 multiplier)
3. Futures & Commodities (contracts, CME initial margin, notional leverage)
4. Cryptocurrencies & 24/7 Perpetuals (spot, leverage margin)
5. Fixed Income & Treasury Instruments (TLT, IEF, notes)

Maintains persistent journal/paper_portfolio.json with a default $1,000,000.00 cash balance,
live mark-to-market valuations, real-time P&L tracking, and HMAC-SHA256 provenance receipts.
"""

import os
import json
import datetime
import math
from typing import Dict, Any, List, Optional, Tuple
import yfinance as yf
from tools.ledger import ProvenanceLedger

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PORTFOLIO_FILE = os.path.join(PROJECT_DIR, "journal", "paper_portfolio.json")
INITIAL_PORTFOLIO_CASH = 1000000.0  # $1,000,000.00 Simulation Capital


class PaperTradingEngine:
    """
    Institutional paper trading execution engine.
    Executes real-market orders against live quotes, validates cash & margin headroom,
    and updates the active portfolio book in real-time.
    """

    def __init__(self, portfolio_file: Optional[str] = None, ledger: Optional[ProvenanceLedger] = None):
        self.portfolio_file = portfolio_file or PORTFOLIO_FILE
        self.ledger = ledger or ProvenanceLedger(run_id="paper_trading")
        self._ensure_portfolio_file()

    def _ensure_portfolio_file(self) -> None:
        """Initialize paper_portfolio.json if it doesn't exist."""
        os.makedirs(os.path.dirname(self.portfolio_file), exist_ok=True)
        if not os.path.exists(self.portfolio_file):
            initial_state = {
                "initial_cash": INITIAL_PORTFOLIO_CASH,
                "cash_balance": INITIAL_PORTFOLIO_CASH,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "positions": [],
                "closed_trades": [],
                "total_realized_pnl": 0.0,
                "total_unrealized_pnl": 0.0,
                "total_equity": INITIAL_PORTFOLIO_CASH
            }
            with open(self.portfolio_file, "w", encoding="utf-8") as f:
                json.dump(initial_state, f, indent=2)

    def load_portfolio(self) -> Dict[str, Any]:
        """Load portfolio state from disk."""
        self._ensure_portfolio_file()
        try:
            with open(self.portfolio_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception:
            # Fallback reinitialization if file is corrupted
            self.reset_portfolio()
            with open(self.portfolio_file, "r", encoding="utf-8") as f:
                return json.load(f)

    def save_portfolio(self, data: Dict[str, Any]) -> None:
        """Persist portfolio state to disk."""
        data["last_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(self.portfolio_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def execute_trade(
        self,
        symbol: str,
        asset_class: str,
        side: str,
        quantity: float,
        price: float,
        strategy_type: str = "Standard",
        multiplier: float = 1.0,
        margin_per_unit: float = 0.0,
        legs: Optional[List[Dict[str, Any]]] = None,
        notes: str = ""
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Execute an order mirroring real live market conditions:
        - Validates sufficient cash or margin headroom.
        - Calculates total cost basis or margin requirement.
        - Debits cash balance.
        - Signs transaction with HMAC-SHA256 provenance ledger.
        - Adds position to the active portfolio book.
        """
        sym = (symbol or "").strip().upper()
        clean_side = (side or "BUY").strip().upper()
        clean_asset = (asset_class or "Equities").strip()
        qty = float(quantity)
        px = float(price)
        mult = float(multiplier)

        if not sym:
            return False, "Error: Ticker or symbol is required for execution.", {}
        if qty <= 0:
            return False, "Error: Trade quantity must be greater than zero.", {}
        if px <= 0:
            return False, "Error: Execution price must be greater than zero.", {}

        data = self.load_portfolio()
        cash = float(data.get("cash_balance", INITIAL_PORTFOLIO_CASH))

        # Determine capital commitment / margin
        if clean_asset == "Options":
            mult = 100.0 if mult == 1.0 else mult
            cost = round(qty * px * mult, 2)
        elif clean_asset == "Futures":
            # For futures, margin_per_unit is the exchange initial margin
            margin_unit = margin_per_unit if margin_per_unit > 0 else (px * mult * 0.10)
            cost = round(qty * margin_unit, 2)
        elif clean_asset == "Crypto":
            margin_rate = 0.10 if margin_per_unit > 0 else 1.0
            cost = round(qty * px * margin_rate, 2)
        else:
            # Equities / ETFs / Bonds
            cost = round(qty * px * mult, 2)

        # Check cash headroom for Long/Buy orders
        if clean_side == "BUY":
            if cost > cash:
                return (
                    False,
                    f"Insufficient Cash: Order requires ${cost:,.2f} USD, but available cash is ${cash:,.2f} USD.",
                    {}
                )
            new_cash = round(cash - cost, 2)
        else:
            # Short order: requires initial margin or credits cash
            if cost > cash:
                return (
                    False,
                    f"Insufficient Margin: Short position requires ${cost:,.2f} USD margin buffer.",
                    {}
                )
            new_cash = round(cash - cost, 2)

        # Create unique position & order identifiers
        order_num = len(data.get("positions", [])) + len(data.get("closed_trades", [])) + 1
        pos_id = f"POS_{order_num:04d}"
        ord_id = f"ORD_{order_num:04d}"
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Sign order in Provenance Ledger
        ledger_id = self.ledger.record(
            tool="LivePaperTradingExecution",
            inputs={
                "order_id": ord_id,
                "position_id": pos_id,
                "symbol": sym,
                "asset_class": clean_asset,
                "strategy": strategy_type,
                "side": clean_side,
                "quantity": qty,
                "execution_price": px,
                "multiplier": mult,
                "cost_basis": cost
            },
            output={
                "status": "FILLED",
                "fill_timestamp": timestamp,
                "remaining_cash": new_cash
            },
            source="Live Paper Trading Execution Desk"
        )

        position = {
            "position_id": pos_id,
            "order_id": ord_id,
            "symbol": sym,
            "asset_class": clean_asset,
            "strategy_type": strategy_type,
            "side": clean_side,
            "quantity": qty,
            "entry_price": px,
            "current_price": px,
            "multiplier": mult,
            "margin_committed": cost if clean_asset == "Futures" else 0.0,
            "cost_basis": cost,
            "market_value": cost,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0,
            "opened_at": timestamp,
            "legs": legs or [],
            "notes": notes,
            "ledger_id": ledger_id
        }

        data["cash_balance"] = new_cash
        data["positions"].append(position)
        self.save_portfolio(data)

        # Recalculate totals
        self.mark_to_market()

        msg = (
            f"✅ ORDER FILLED [{ord_id}]: {clean_side} {qty:,.2f} {sym} @ ${px:,.2f} "
            f"(${cost:,.2f} Total) | Ledger: {ledger_id}"
        )
        return True, msg, position

    def close_position(
        self,
        position_id: str,
        exit_price: Optional[float] = None,
        reason: str = "Market Close"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Close an open position at the specified or live market price:
        - Calculates realized P&L and return %.
        - Credits cash balance with returned capital and profits/losses.
        - Moves record from positions to closed_trades.
        - Signs execution receipt with Provenance Ledger.
        """
        data = self.load_portfolio()
        positions = data.get("positions", [])

        target_idx = None
        for i, pos in enumerate(positions):
            if pos["position_id"] == position_id:
                target_idx = i
                break

        if target_idx is None:
            return False, f"Position '{position_id}' not found in active portfolio.", {}

        pos = positions.pop(target_idx)
        sym = pos["symbol"]
        qty = pos["quantity"]
        entry_px = pos["entry_price"]
        mult = pos["multiplier"]
        cost_basis = pos["cost_basis"]
        side = pos["side"]
        asset_class = pos["asset_class"]

        # If exit_price is not provided, fetch current live quote
        if exit_price is None or exit_price <= 0:
            try:
                t = yf.Ticker(sym)
                fi = getattr(t, "fast_info", None)
                px_val = getattr(fi, "last_price", None) or getattr(fi, "previous_close", None)
                px = float(px_val) if px_val else entry_px
            except Exception:
                px = entry_px
        else:
            px = float(exit_price)

        # Calculate realized P&L
        if asset_class == "Futures":
            # Futures PnL = (Exit - Entry) * Qty * Multiplier
            if side == "BUY":
                realized_pnl = (px - entry_px) * qty * mult
            else:
                realized_pnl = (entry_px - px) * qty * mult
            returned_capital = pos["margin_committed"] + realized_pnl
        elif asset_class == "Options":
            # Options PnL = (Exit - Entry) * Qty * 100
            proceeds = px * qty * mult
            if side == "BUY":
                realized_pnl = proceeds - cost_basis
                returned_capital = proceeds
            else:
                realized_pnl = cost_basis - proceeds
                returned_capital = cost_basis + realized_pnl
        else:
            # Equities / Crypto
            proceeds = px * qty * mult
            if side == "BUY":
                realized_pnl = proceeds - cost_basis
                returned_capital = proceeds
            else:
                realized_pnl = cost_basis - proceeds
                returned_capital = cost_basis + realized_pnl

        realized_pnl = round(realized_pnl, 2)
        returned_capital = round(max(0.0, returned_capital), 2)
        ret_pct = round((realized_pnl / cost_basis) * 100.0, 2) if cost_basis > 0 else 0.0

        cash = float(data.get("cash_balance", INITIAL_PORTFOLIO_CASH))
        new_cash = round(cash + returned_capital, 2)

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Sign closing receipt in Provenance Ledger
        ledger_id = self.ledger.record(
            tool="LivePaperTradingClosing",
            inputs={
                "position_id": position_id,
                "symbol": sym,
                "exit_price": px,
                "entry_price": entry_px,
                "quantity": qty,
                "reason": reason
            },
            output={
                "realized_pnl_usd": realized_pnl,
                "realized_return_pct": ret_pct,
                "credited_cash": returned_capital,
                "new_cash_balance": new_cash,
                "closed_at": timestamp
            },
            source="Live Paper Trading Closing Desk"
        )

        closed_record = {
            "position_id": position_id,
            "symbol": sym,
            "asset_class": asset_class,
            "strategy_type": pos["strategy_type"],
            "side": side,
            "quantity": qty,
            "entry_price": entry_px,
            "exit_price": px,
            "multiplier": mult,
            "cost_basis": cost_basis,
            "realized_pnl": realized_pnl,
            "realized_pnl_pct": ret_pct,
            "opened_at": pos["opened_at"],
            "closed_at": timestamp,
            "close_reason": reason,
            "ledger_id": ledger_id
        }

        data["cash_balance"] = new_cash
        data["positions"] = positions
        data.setdefault("closed_trades", []).append(closed_record)
        data["total_realized_pnl"] = round(
            sum(t.get("realized_pnl", 0.0) for t in data["closed_trades"]), 2
        )
        self.save_portfolio(data)
        self.mark_to_market()

        sign_sym = "+" if realized_pnl >= 0 else ""
        msg = (
            f"✅ CLOSED [{position_id}]: {side} {qty} {sym} @ ${px:,.2f} | "
            f"P&L: {sign_sym}${realized_pnl:,.2f} ({sign_sym}{ret_pct:.2f}%) | "
            f"Cash Balance: ${new_cash:,.2f} | Ledger: {ledger_id}"
        )
        return True, msg, closed_record

    def mark_to_market(self, quotes: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Recalculate real-time mark-to-market valuations and unrealized P&L
        for all active positions using live quotes.
        """
        data = self.load_portfolio()
        positions = data.get("positions", [])
        provided_quotes = quotes or {}

        total_unrealized = 0.0
        total_open_value = 0.0

        for pos in positions:
            sym = pos["symbol"]
            qty = pos["quantity"]
            entry_px = pos["entry_price"]
            mult = pos["multiplier"]
            cost_basis = pos["cost_basis"]
            side = pos["side"]
            asset_class = pos["asset_class"]

            # Lookup current market price
            if sym in provided_quotes:
                curr_px = float(provided_quotes[sym])
            else:
                try:
                    t = yf.Ticker(sym)
                    fi = getattr(t, "fast_info", None)
                    p_val = getattr(fi, "last_price", None) or getattr(fi, "previous_close", None)
                    curr_px = float(p_val) if p_val else entry_px
                except Exception:
                    curr_px = entry_px

            curr_px = round(curr_px, 2)
            pos["current_price"] = curr_px

            # Value & Unrealized PnL calculation
            if asset_class == "Futures":
                if side == "BUY":
                    unrealized = (curr_px - entry_px) * qty * mult
                else:
                    unrealized = (entry_px - curr_px) * qty * mult
                mkt_val = pos.get("margin_committed", 0.0) + unrealized
            elif asset_class == "Options":
                mkt_val = curr_px * qty * mult
                if side == "BUY":
                    unrealized = mkt_val - cost_basis
                else:
                    unrealized = cost_basis - mkt_val
            else:
                # Equities / Crypto / Bonds
                mkt_val = curr_px * qty * mult
                if side == "BUY":
                    unrealized = mkt_val - cost_basis
                else:
                    unrealized = cost_basis - mkt_val

            unrealized = round(unrealized, 2)
            mkt_val = round(max(0.0, mkt_val), 2)
            pnl_pct = round((unrealized / cost_basis) * 100.0, 2) if cost_basis > 0 else 0.0

            pos["market_value"] = mkt_val
            pos["unrealized_pnl"] = unrealized
            pos["unrealized_pnl_pct"] = pnl_pct

            total_unrealized += unrealized
            total_open_value += mkt_val

        cash = float(data.get("cash_balance", INITIAL_PORTFOLIO_CASH))
        total_equity = round(cash + total_open_value, 2)
        initial_cash = float(data.get("initial_cash", INITIAL_PORTFOLIO_CASH))
        tot_return_pct = round(((total_equity - initial_cash) / initial_cash) * 100.0, 2)

        data["positions"] = positions
        data["total_unrealized_pnl"] = round(total_unrealized, 2)
        data["total_equity"] = total_equity
        data["total_open_value"] = round(total_open_value, 2)
        data["portfolio_return_pct"] = tot_return_pct

        self.save_portfolio(data)
        return data

    mark_to_market_portfolio = mark_to_market

    def reset_portfolio(self, initial_cash: float = INITIAL_PORTFOLIO_CASH) -> Dict[str, Any]:
        """Reset paper portfolio back to initial $1,000,000.00 cash balance."""
        os.makedirs(os.path.dirname(self.portfolio_file), exist_ok=True)
        reset_state = {
            "initial_cash": float(initial_cash),
            "cash_balance": float(initial_cash),
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "positions": [],
            "closed_trades": [],
            "total_realized_pnl": 0.0,
            "total_unrealized_pnl": 0.0,
            "total_open_value": 0.0,
            "total_equity": float(initial_cash),
            "portfolio_return_pct": 0.0
        }
        with open(self.portfolio_file, "w", encoding="utf-8") as f:
            json.dump(reset_state, f, indent=2)
        return reset_state


_ENGINE_INSTANCE: Optional[PaperTradingEngine] = None


def get_paper_trading_engine() -> PaperTradingEngine:
    """Singleton getter for PaperTradingEngine."""
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        _ENGINE_INSTANCE = PaperTradingEngine()
    return _ENGINE_INSTANCE
