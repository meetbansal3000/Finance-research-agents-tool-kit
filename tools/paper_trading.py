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
from typing import Dict, Any, List, Optional, Tuple, Union
import yfinance as yf
from tools.ledger import ProvenanceLedger
from tools.broker_client import ExecutionCostModel, MultiExchangeRouter
from tools.fill_model import RealisticFillModel

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PORTFOLIO_FILE = os.path.join(PROJECT_DIR, "journal", "paper_portfolio.json")

CURRENCY_SYMBOLS: Dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CAD": "CA$",
    "AUD": "A$",
    "CHF": "CHF ",
    "INR": "₹"
}

def get_currency_symbol(currency: str = "USD") -> str:
    """Return the display symbol for a given currency code."""
    return CURRENCY_SYMBOLS.get((currency or "USD").strip().upper(), f"{(currency or 'USD').strip().upper()} ")

# Configurable starting capital: defaults to environment variable or $100,000.00 (NOT $1,000,000)
DEFAULT_STARTING_CAPITAL = float(os.getenv("STARTING_CAPITAL", os.getenv("PAPER_STARTING_CAPITAL", "100000.0")))
DEFAULT_CURRENCY = os.getenv("PORTFOLIO_CURRENCY", os.getenv("CURRENCY", "USD")).strip().upper()
INITIAL_PORTFOLIO_CASH = DEFAULT_STARTING_CAPITAL


class PaperTradingEngine:
    """
    Institutional paper trading execution engine.
    Executes real-market orders against live quotes, validates cash & margin headroom,
    and updates the active portfolio book in real-time.
    Supports user-configurable starting capital and multi-currency accounting.
    """

    def __init__(
        self,
        portfolio_file: Optional[str] = None,
        ledger: Optional[ProvenanceLedger] = None,
        router: Optional[MultiExchangeRouter] = None,
        initial_capital: Optional[float] = None,
        currency: Optional[str] = None
    ):
        self.portfolio_file = portfolio_file or PORTFOLIO_FILE
        self.ledger = ledger or ProvenanceLedger(run_id="paper_trading")
        self.router = router or MultiExchangeRouter()
        self.initial_capital = float(initial_capital) if initial_capital is not None else DEFAULT_STARTING_CAPITAL
        self.currency = (currency or DEFAULT_CURRENCY).strip().upper()
        self._ensure_portfolio_file()

    def _ensure_portfolio_file(self) -> None:
        """Initialize paper_portfolio.json if it doesn't exist."""
        os.makedirs(os.path.dirname(self.portfolio_file), exist_ok=True)
        if not os.path.exists(self.portfolio_file):
            sym = get_currency_symbol(self.currency)
            initial_state = {
                "initial_cash": self.initial_capital,
                "cash_balance": self.initial_capital,
                "currency": self.currency,
                "currency_symbol": sym,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "positions": [],
                "closed_trades": [],
                "total_realized_pnl": 0.0,
                "total_unrealized_pnl": 0.0,
                "total_equity": self.initial_capital
            }
            with open(self.portfolio_file, "w", encoding="utf-8") as f:
                json.dump(initial_state, f, indent=2)

    def load_portfolio(self) -> Dict[str, Any]:
        """Load portfolio state from disk."""
        self._ensure_portfolio_file()
        try:
            with open(self.portfolio_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "currency" not in data:
                data["currency"] = self.currency
            if "currency_symbol" not in data:
                data["currency_symbol"] = get_currency_symbol(data["currency"])
            return data
        except Exception:
            # Fallback reinitialization if file is corrupted
            return self.reset_portfolio()

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
        notes: str = "",
        routing_venue: str = "SMART",
        execution_mode: Optional[str] = None,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        quote_timestamp: Optional[Union[float, int, str, datetime.datetime]] = None,
        max_quote_age_seconds: float = 900.0,
        enforce_market_hours: bool = False,
        current_time: Optional[datetime.datetime] = None,
        average_daily_volume: Optional[float] = None,
        max_volume_share: float = 0.10,
        apply_tca_to_cost_basis: bool = False
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Execute an order mirroring real live market conditions:
        - Market orders fill at next price plus modelled spread and slippage.
        - Limit orders fill only if price crosses the limit.
        - Partial fills when order size exceeds max_volume_share of average volume.
        - Rejects trading outside market hours (enforce_market_hours=True) or stale quotes.
        - Computes institutional TCA friction (bid-ask spread, exchange fees, market impact).
        - Debits cash balance / tracks margin requirements.
        - Signs transaction with HMAC-SHA256 provenance ledger.
        """
        sym = (symbol or "").strip().upper()
        clean_side = (side or "BUY").strip().upper()
        clean_asset = (asset_class or "Equities").strip().capitalize()
        qty = float(quantity)
        px = float(price)
        mult = float(multiplier)
        active_mode = execution_mode or self.router.active_mode

        if not sym:
            return False, "Error: Ticker or symbol is required for execution.", {}
        if qty <= 0:
            return False, "Error: Trade quantity must be greater than zero.", {}
        if px <= 0:
            return False, "Error: Execution price must be greater than zero.", {}

        # 1. Market Hours Verification
        if enforce_market_hours:
            hours_ok, hours_msg = RealisticFillModel.check_market_hours(
                asset_class=clean_asset,
                current_time=current_time
            )
            if not hours_ok:
                return False, hours_msg, {
                    "status": "REJECTED_MARKET_CLOSED",
                    "reason": hours_msg,
                    "symbol": sym,
                    "asset_class": clean_asset
                }

        # 2. Quote Freshness Verification
        if quote_timestamp is not None:
            quote_ok, quote_age, quote_msg = RealisticFillModel.check_quote_freshness(
                quote_timestamp=quote_timestamp,
                max_age_seconds=max_quote_age_seconds,
                current_time=current_time
            )
            if not quote_ok:
                return False, quote_msg, {
                    "status": "REJECTED_STALE_QUOTE",
                    "reason": quote_msg,
                    "quote_age_seconds": quote_age,
                    "max_allowed_age_seconds": max_quote_age_seconds,
                    "symbol": sym
                }

        # 3. Volume and Partial Fill Check
        fill_qty, unfilled_qty, is_partial, vol_msg = RealisticFillModel.calculate_volume_fill(
            order_quantity=qty,
            average_daily_volume=average_daily_volume,
            max_volume_share=max_volume_share
        )
        if fill_qty <= 0:
            return False, "Order rejected: zero executable liquidity.", {
                "status": "REJECTED_ZERO_LIQUIDITY",
                "symbol": sym
            }

        # 4. Limit Order Crossing Validation
        clean_type = (order_type or "market").strip().lower()
        eff_limit_px = limit_price if limit_price is not None else px
        if clean_type == "limit":
            cross_ok, cross_msg = RealisticFillModel.evaluate_limit_crossing(
                side=clean_side,
                limit_price=eff_limit_px,
                market_price=px
            )
            if not cross_ok:
                return False, cross_msg, {
                    "status": "UNFILLED",
                    "reason": "PRICE_DID_NOT_CROSS",
                    "order_type": "LIMIT",
                    "limit_price": eff_limit_px,
                    "market_price": px,
                    "side": clean_side,
                    "symbol": sym
                }

        # 5. Compute Institutional Pre-Trade TCA metrics
        adv = average_daily_volume if (average_daily_volume and average_daily_volume > 0) else 500000.0
        tca = ExecutionCostModel.calculate_execution_costs(
            asset_class=clean_asset,
            side=clean_side,
            quantity=fill_qty,
            price=px,
            average_daily_volume=adv
        )
        effective_px = tca["effective_price"]

        # Ensure limit order does not execute worse than limit price
        if clean_type == "limit":
            if clean_side == "BUY" and effective_px > eff_limit_px:
                effective_px = eff_limit_px
                tca["effective_price"] = effective_px
            elif clean_side == "SELL" and effective_px < eff_limit_px:
                effective_px = eff_limit_px
                tca["effective_price"] = effective_px

        data = self.load_portfolio()
        curr_code = data.get("currency", self.currency)
        curr_sym = data.get("currency_symbol", get_currency_symbol(curr_code))
        cash = float(data.get("cash_balance", self.initial_capital))

        # Determine capital commitment / margin
        price_for_cost = effective_px if apply_tca_to_cost_basis else px
        fee_for_cost = tca.get("commission_and_clearing_fees_usd", 0.0) if apply_tca_to_cost_basis else 0.0

        if clean_asset == "Options":
            mult = 100.0 if mult == 1.0 else mult
            cost = round(fill_qty * price_for_cost * mult + fee_for_cost, 2)
        elif clean_asset == "Futures":
            # For futures, margin_per_unit is the exchange initial margin
            margin_unit = margin_per_unit if margin_per_unit > 0 else (price_for_cost * mult * 0.10)
            cost = round(fill_qty * margin_unit + fee_for_cost, 2)
        elif clean_asset == "Crypto":
            margin_rate = 0.10 if margin_per_unit > 0 else 1.0
            cost = round(fill_qty * price_for_cost * margin_rate + fee_for_cost, 2)
        else:
            # Equities / ETFs / Bonds
            cost = round(fill_qty * price_for_cost * mult + fee_for_cost, 2)

        # Check cash headroom for Long/Buy orders
        if clean_side == "BUY":
            if cost > cash:
                return (
                    False,
                    f"Insufficient Cash: Order requires {curr_sym}{cost:,.2f} {curr_code}, but available cash is {curr_sym}{cash:,.2f} {curr_code}.",
                    {}
                )
            new_cash = round(cash - cost, 2)
        else:
            # Short order: requires initial margin or credits cash
            if cost > cash:
                return (
                    False,
                    f"Insufficient Margin: Short position requires {curr_sym}{cost:,.2f} {curr_code} margin buffer.",
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
                "order_type": clean_type.upper(),
                "quantity": fill_qty,
                "requested_quantity": qty,
                "unfilled_quantity": unfilled_qty,
                "is_partial": is_partial,
                "execution_price": px,
                "effective_price": effective_px,
                "routing_venue": routing_venue,
                "execution_mode": active_mode,
                "multiplier": mult,
                "cost_basis": cost,
                "tca_friction_usd": tca.get("total_friction_usd", 0.0)
            },
            output={
                "status": "PARTIALLY_FILLED" if is_partial else "FILLED",
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
            "order_type": clean_type.upper(),
            "quantity": fill_qty,
            "requested_quantity": qty,
            "unfilled_quantity": unfilled_qty,
            "is_partial": is_partial,
            "entry_price": px,
            "effective_entry_price": effective_px,
            "current_price": px,
            "multiplier": mult,
            "margin_committed": cost if clean_asset == "Futures" else 0.0,
            "cost_basis": cost,
            "market_value": cost,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0,
            "routing_venue": routing_venue,
            "execution_mode": active_mode,
            "tca": tca,
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

        status_tag = "ORDER PARTIALLY FILLED" if is_partial else "ORDER FILLED"
        msg = (
            f"✅ {status_tag} [{ord_id} via {routing_venue}]: {clean_side} {fill_qty:,.2f} {sym} @ {curr_sym}{effective_px:,.4f} "
            f"({curr_sym}{cost:,.2f} Total {curr_code} | TCA Friction: {curr_sym}{tca['total_friction_usd']:,.2f}) | Ledger: {ledger_id}"
        )
        if is_partial:
            msg += f" | {unfilled_qty:,.2f} remaining unfilled"

        # Dispatch Order Fill Webhook notification
        try:
            from tools.alert_dispatcher import get_alert_dispatcher
            get_alert_dispatcher().dispatch_order_fill(order_record=position, tca=tca)
        except Exception:
            pass

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

        curr_code = data.get("currency", self.currency)
        curr_sym = data.get("currency_symbol", get_currency_symbol(curr_code))
        sign_sym = "+" if realized_pnl >= 0 else ""
        msg = (
            f"✅ CLOSED [{position_id}]: {side} {qty} {sym} @ {curr_sym}{px:,.2f} {curr_code} | "
            f"P&L: {sign_sym}{curr_sym}{realized_pnl:,.2f} ({sign_sym}{ret_pct:.2f}%) | "
            f"Cash Balance: {curr_sym}{new_cash:,.2f} {curr_code} | Ledger: {ledger_id}"
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

    def apply_dividend(
        self,
        symbol: str,
        dividend_per_share: float,
        ex_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply a cash dividend distribution to open positions:
        - Long positions receive cash: quantity * dividend_per_share.
        - Short positions pay cash: quantity * dividend_per_share.
        Updates cash balance and records provenance ledger receipt.
        """
        sym = (symbol or "").strip().upper()
        div = float(dividend_per_share)
        if div <= 0:
            return {"success": False, "message": "Dividend per share must be positive."}

        data = self.load_portfolio()
        cash = float(data.get("cash_balance", INITIAL_PORTFOLIO_CASH))
        positions = data.get("positions", [])

        adjusted_positions = []
        total_credited = 0.0
        total_debited = 0.0

        for pos in positions:
            if pos.get("symbol", "").upper() == sym and pos.get("asset_class", "Equities") in ["Equities", "ETFs"]:
                qty = float(pos.get("quantity", 0.0))
                side = pos.get("side", "BUY").upper()
                amt = round(qty * div, 2)
                if side == "BUY":
                    total_credited += amt
                    pos_action = f"Credited +${amt:,.2f}"
                else:
                    total_debited += amt
                    pos_action = f"Debited -${amt:,.2f}"

                pos.setdefault("dividend_history", []).append({
                    "dividend_per_share": div,
                    "ex_date": ex_date or datetime.date.today().isoformat(),
                    "total_amount": amt,
                    "action": pos_action,
                    "applied_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                })
                adjusted_positions.append({
                    "position_id": pos.get("position_id"),
                    "side": side,
                    "quantity": qty,
                    "amount": amt,
                    "action": pos_action
                })

        net_adjustment = round(total_credited - total_debited, 2)
        new_cash = round(cash + net_adjustment, 2)
        data["cash_balance"] = new_cash
        self.save_portfolio(data)
        self.mark_to_market()

        ledger_id = self.ledger.record(
            tool="PaperTradingEngine.apply_dividend",
            inputs={"symbol": sym, "dividend_per_share": div, "ex_date": ex_date},
            output={"net_cash_adjustment": net_adjustment, "new_cash": new_cash, "affected_count": len(adjusted_positions)},
            source="Corporate Actions Desk",
            ticker=sym
        )

        return {
            "success": True,
            "symbol": sym,
            "dividend_per_share": div,
            "positions_adjusted": adjusted_positions,
            "total_credited_usd": total_credited,
            "total_debited_usd": total_debited,
            "net_cash_adjustment_usd": net_adjustment,
            "new_cash_balance": new_cash,
            "ledger_id": ledger_id
        }

    def apply_stock_split(
        self,
        symbol: str,
        ratio: float
    ) -> Dict[str, Any]:
        """
        Apply a stock split to open equity positions:
        - Position quantity multiplied by ratio (e.g. 2.0 for 2:1, 0.5 for 1:2 reverse).
        - Entry price and current price divided by ratio.
        - Total cost basis preserved unchanged.
        """
        sym = (symbol or "").strip().upper()
        split_ratio = float(ratio)
        if split_ratio <= 0:
            return {"success": False, "message": "Split ratio must be positive."}

        data = self.load_portfolio()
        positions = data.get("positions", [])
        adjusted_positions = []

        for pos in positions:
            if pos.get("symbol", "").upper() == sym and pos.get("asset_class", "Equities") in ["Equities", "ETFs"]:
                old_qty = float(pos.get("quantity", 0.0))
                old_entry = float(pos.get("entry_price", 0.0))
                new_qty = round(old_qty * split_ratio, 6)
                new_entry = round(old_entry / split_ratio, 4)

                pos["quantity"] = new_qty
                pos["entry_price"] = new_entry
                if "effective_entry_price" in pos:
                    pos["effective_entry_price"] = round(float(pos["effective_entry_price"]) / split_ratio, 4)
                if "current_price" in pos:
                    pos["current_price"] = round(float(pos["current_price"]) / split_ratio, 4)

                pos.setdefault("corporate_actions", []).append({
                    "action": "STOCK_SPLIT",
                    "split_ratio": split_ratio,
                    "old_quantity": old_qty,
                    "new_quantity": new_qty,
                    "old_entry_price": old_entry,
                    "new_entry_price": new_entry,
                    "applied_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                })
                adjusted_positions.append({
                    "position_id": pos.get("position_id"),
                    "old_quantity": old_qty,
                    "new_quantity": new_qty,
                    "old_entry_price": old_entry,
                    "new_entry_price": new_entry
                })

        self.save_portfolio(data)
        self.mark_to_market()

        ledger_id = self.ledger.record(
            tool="PaperTradingEngine.apply_stock_split",
            inputs={"symbol": sym, "ratio": split_ratio},
            output={"adjusted_positions_count": len(adjusted_positions)},
            source="Corporate Actions Desk",
            ticker=sym
        )

        return {
            "success": True,
            "symbol": sym,
            "split_ratio": split_ratio,
            "adjusted_positions": adjusted_positions,
            "ledger_id": ledger_id
        }

    def apply_short_borrow_cost(
        self,
        days: int = 1,
        annual_borrow_rate: float = 0.03
    ) -> Dict[str, Any]:
        """
        Accrue and deduct short borrow financing costs for all open short positions:
        Borrow Cost = Notional Value * (annual_borrow_rate / 360) * days
        Debits cash balance and tracks cumulative borrow fee per position.
        """
        data = self.load_portfolio()
        cash = float(data.get("cash_balance", INITIAL_PORTFOLIO_CASH))
        positions = data.get("positions", [])

        total_cost = 0.0
        details = []

        daily_rate = float(annual_borrow_rate) / 360.0

        for pos in positions:
            if pos.get("side", "").upper() == "SELL":
                qty = float(pos.get("quantity", 0.0))
                px = float(pos.get("current_price", pos.get("entry_price", 0.0)))
                mult = float(pos.get("multiplier", 1.0))
                notional = qty * px * mult
                cost = round(notional * daily_rate * float(days), 2)
                total_cost += cost

                pos["accumulated_borrow_fees"] = round(
                    float(pos.get("accumulated_borrow_fees", 0.0)) + cost, 2
                )
                details.append({
                    "position_id": pos.get("position_id"),
                    "symbol": pos.get("symbol"),
                    "notional": notional,
                    "borrow_cost_usd": cost,
                    "days": days,
                    "annual_borrow_rate": annual_borrow_rate
                })

        total_cost = round(total_cost, 2)
        new_cash = round(cash - total_cost, 2)
        data["cash_balance"] = new_cash
        self.save_portfolio(data)
        self.mark_to_market()

        ledger_id = self.ledger.record(
            tool="PaperTradingEngine.apply_short_borrow_cost",
            inputs={"days": days, "annual_borrow_rate": annual_borrow_rate},
            output={"total_borrow_cost_usd": total_cost, "new_cash": new_cash},
            source="Financing & Margin Desk"
        )

        return {
            "success": True,
            "days": days,
            "annual_borrow_rate": annual_borrow_rate,
            "total_borrow_cost_usd": total_cost,
            "new_cash_balance": new_cash,
            "positions_charged": details,
            "ledger_id": ledger_id
        }

    def reset_portfolio(
        self,
        initial_cash: Optional[float] = None,
        currency: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reset paper portfolio back to initial cash balance and currency."""
        os.makedirs(os.path.dirname(self.portfolio_file), exist_ok=True)
        init_c = float(initial_cash) if initial_cash is not None else self.initial_capital
        curr = (currency or self.currency).strip().upper()
        sym = get_currency_symbol(curr)
        self.initial_capital = init_c
        self.currency = curr
        reset_state = {
            "initial_cash": init_c,
            "cash_balance": init_c,
            "currency": curr,
            "currency_symbol": sym,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "positions": [],
            "closed_trades": [],
            "total_realized_pnl": 0.0,
            "total_unrealized_pnl": 0.0,
            "total_open_value": 0.0,
            "total_equity": init_c,
            "portfolio_return_pct": 0.0
        }
        with open(self.portfolio_file, "w", encoding="utf-8") as f:
            json.dump(reset_state, f, indent=2)
        return reset_state

    def set_starting_capital(
        self,
        amount: float,
        currency: str = "USD",
        reset_positions: bool = False
    ) -> Dict[str, Any]:
        """Configure starting capital and currency."""
        amt = float(amount)
        curr = currency.strip().upper()
        self.initial_capital = amt
        self.currency = curr
        if reset_positions:
            return self.reset_portfolio(initial_cash=amt, currency=curr)
        data = self.load_portfolio()
        old_init = float(data.get("initial_cash", amt))
        delta = amt - old_init
        data["initial_cash"] = amt
        data["cash_balance"] = round(float(data.get("cash_balance", amt)) + delta, 2)
        data["currency"] = curr
        data["currency_symbol"] = get_currency_symbol(curr)
        self.save_portfolio(data)
        self.mark_to_market()
        return data


_ENGINE_INSTANCE: Optional[PaperTradingEngine] = None


def get_paper_trading_engine() -> PaperTradingEngine:
    """Singleton getter for PaperTradingEngine."""
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        _ENGINE_INSTANCE = PaperTradingEngine()
    return _ENGINE_INSTANCE
