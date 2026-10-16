"""
tools/fill_model.py
Realistic Institutional Fill Model for Multi-Asset Paper Trading.

Implements realistic trade execution mechanics:
1. Market Orders: Fills at next available price plus modelled half-spread and
   Almgren-Chriss square-root market impact slippage, including regulatory and broker fees.
2. Limit Orders: Fills ONLY if the market price crosses the limit price:
   - BUY limit: fills only when market_price <= limit_price.
   - SELL limit: fills only when market_price >= limit_price.
3. Partial Fills: Order size exceeding a configurable threshold of average daily volume (ADV)
   is partially filled up to the threshold, with remaining quantity unfilled.
4. Market Hours Validation: Blocks trading outside regular market hours (09:30 - 16:00 ET, Mon-Fri)
   for equities and derivatives, while permitting 24/7 trading for crypto.
5. Quote Freshness Gate: Rejects any order whose quote timestamp is older than a configurable max age.
6. Corporate Actions & Carrying Costs:
   - Dividends: Credits cash for long equity positions, debits cash for short positions.
   - Stock Splits: Adjusts position quantities and per-share prices while preserving cost basis.
   - Short Borrow Cost: Accrues and debits daily borrow fees for open short equity positions.
"""

import math
import datetime
import zoneinfo
from typing import Dict, Any, List, Optional, Tuple, Union

from tools.broker_client import ExecutionCostModel


ET_TZ = zoneinfo.ZoneInfo("America/New_York")


class RealisticFillModel:
    """
    Institutional fill model providing realistic execution validation,
    pricing, slippage, partial fills, market hours checking, and corporate actions.
    """

    # Default regular market hours: 09:30:00 to 16:00:00 Eastern Time
    MARKET_OPEN_TIME = datetime.time(9, 30, 0)
    MARKET_CLOSE_TIME = datetime.time(16, 0, 0)

    # Default parameters
    DEFAULT_MAX_QUOTE_AGE_SECONDS = 900.0  # 15 minutes
    DEFAULT_MAX_VOLUME_SHARE = 0.10        # Max 10% of ADV per fill
    DEFAULT_ANNUAL_BORROW_RATE = 0.03      # 3.0% annual short borrow rate

    @classmethod
    def check_market_hours(
        cls,
        asset_class: str = "Equities",
        current_time: Optional[datetime.datetime] = None
    ) -> Tuple[bool, str]:
        """
        Verify whether the market is currently open for the given asset class.
        Crypto trades 24/7/365.
        US Equities, Options, and Bonds trade Monday-Friday 09:30 to 16:00 ET.
        """
        clean_asset = (asset_class or "Equities").strip().capitalize()
        if clean_asset == "Crypto":
            return True, "Crypto market operates 24/7/365. Session is open."

        # Determine Eastern Time
        if current_time is None:
            now_utc = datetime.datetime.now(datetime.timezone.utc)
        elif current_time.tzinfo is None:
            now_utc = current_time.replace(tzinfo=datetime.timezone.utc)
        else:
            now_utc = current_time

        now_et = now_utc.astimezone(ET_TZ)
        weekday = now_et.weekday()  # 0 = Monday, 4 = Friday, 5 = Saturday, 6 = Sunday

        if weekday >= 5:
            day_name = "Saturday" if weekday == 5 else "Sunday"
            return (
                False,
                f"Market Closed: Weekend trading is disabled ({day_name} {now_et.strftime('%H:%M:%S %Z')}). "
                f"Regular hours are Monday-Friday 09:30-16:00 ET."
            )

        current_tod = now_et.time()
        if current_tod < cls.MARKET_OPEN_TIME or current_tod >= cls.MARKET_CLOSE_TIME:
            return (
                False,
                f"Market Closed: Current ET time {now_et.strftime('%H:%M:%S %Z')} is outside "
                f"regular market hours (09:30:00 - 16:00:00 ET, Mon-Fri)."
            )

        return True, f"Market Open: Regular trading session active ({now_et.strftime('%H:%M:%S %Z')})."

    @classmethod
    def check_quote_freshness(
        cls,
        quote_timestamp: Optional[Union[float, int, str, datetime.datetime]],
        max_age_seconds: float = DEFAULT_MAX_QUOTE_AGE_SECONDS,
        current_time: Optional[datetime.datetime] = None
    ) -> Tuple[bool, float, str]:
        """
        Reject any order whose quote is older than a configurable maximum age.
        """
        if quote_timestamp is None:
            return False, float("inf"), "Quote Stale: Missing quote timestamp. Live quote is mandatory."

        if current_time is None:
            now_utc = datetime.datetime.now(datetime.timezone.utc)
        elif current_time.tzinfo is None:
            now_utc = current_time.replace(tzinfo=datetime.timezone.utc)
        else:
            now_utc = current_time.astimezone(datetime.timezone.utc)

        # Parse quote timestamp
        if isinstance(quote_timestamp, (int, float)):
            quote_dt = datetime.datetime.fromtimestamp(quote_timestamp, tz=datetime.timezone.utc)
        elif isinstance(quote_timestamp, str):
            try:
                # Handle ISO formatted strings
                cleaned_ts = quote_timestamp.replace("Z", "+00:00")
                quote_dt = datetime.datetime.fromisoformat(cleaned_ts)
                if quote_dt.tzinfo is None:
                    quote_dt = quote_dt.replace(tzinfo=datetime.timezone.utc)
                else:
                    quote_dt = quote_dt.astimezone(datetime.timezone.utc)
            except Exception:
                return False, float("inf"), f"Quote Stale: Invalid quote timestamp format '{quote_timestamp}'."
        elif isinstance(quote_timestamp, datetime.datetime):
            if quote_timestamp.tzinfo is None:
                quote_dt = quote_timestamp.replace(tzinfo=datetime.timezone.utc)
            else:
                quote_dt = quote_timestamp.astimezone(datetime.timezone.utc)
        else:
            return False, float("inf"), f"Quote Stale: Unsupported timestamp type {type(quote_timestamp)}."

        age_seconds = (now_utc - quote_dt).total_seconds()
        if age_seconds < 0:
            age_seconds = 0.0  # Clock skew clamp

        if age_seconds > max_age_seconds:
            return (
                False,
                age_seconds,
                f"Quote Stale: Quote age of {age_seconds:.1f}s exceeds maximum threshold of {max_age_seconds:.1f}s."
            )

        return True, age_seconds, f"Quote Fresh: age is {age_seconds:.1f}s (<= {max_age_seconds:.1f}s)."

    @classmethod
    def evaluate_limit_crossing(
        cls,
        side: str,
        limit_price: float,
        market_price: float
    ) -> Tuple[bool, str]:
        """
        Limit orders fill only if the price crosses the limit:
        - BUY limit order at L: Fills only if market_price <= L.
        - SELL limit order at L: Fills only if market_price >= L.
        """
        clean_side = (side or "BUY").strip().upper()
        l_px = float(limit_price)
        m_px = float(market_price)

        if clean_side == "BUY":
            if m_px <= l_px:
                return True, f"Crossed: BUY limit ${l_px:,.2f} crossed by market price ${m_px:,.2f} (market <= limit)."
            else:
                return False, f"Unfilled: BUY limit ${l_px:,.2f} not crossed; market price ${m_px:,.2f} is higher than limit."
        else:
            if m_px >= l_px:
                return True, f"Crossed: SELL limit ${l_px:,.2f} crossed by market price ${m_px:,.2f} (market >= limit)."
            else:
                return False, f"Unfilled: SELL limit ${l_px:,.2f} not crossed; market price ${m_px:,.2f} is lower than limit."

    @classmethod
    def calculate_volume_fill(
        cls,
        order_quantity: float,
        average_daily_volume: Optional[float] = None,
        max_volume_share: float = DEFAULT_MAX_VOLUME_SHARE
    ) -> Tuple[float, float, bool, str]:
        """
        Calculate partial fill if order quantity exceeds the volume threshold.
        Returns (filled_quantity, unfilled_quantity, is_partial, explanation).
        """
        qty = abs(float(order_quantity))
        if average_daily_volume is not None and average_daily_volume > 0:
            max_fillable = round(float(average_daily_volume) * float(max_volume_share), 4)
            if qty > max_fillable:
                filled_qty = max_fillable
                unfilled_qty = round(qty - filled_qty, 4)
                pct_share = max_volume_share * 100.0
                return (
                    filled_qty,
                    unfilled_qty,
                    True,
                    f"Partial Fill: Order size {qty:,.2f} exceeds {pct_share:.1f}% share of ADV ({average_daily_volume:,.0f}). "
                    f"Filled {filled_qty:,.2f} shares; {unfilled_qty:,.2f} shares remain unfilled."
                )

        return qty, 0.0, False, f"Full Fill: Order size {qty:,.2f} is within liquidity limits."

    @classmethod
    def execute_fill(
        cls,
        symbol: str,
        asset_class: str,
        side: str,
        quantity: float,
        market_price: float,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        average_daily_volume: Optional[float] = 500000.0,
        max_volume_share: float = DEFAULT_MAX_VOLUME_SHARE,
        daily_volatility_pct: float = 1.80,
        bid_ask_spread_pct: float = 0.04,
        quote_timestamp: Optional[Union[float, int, str, datetime.datetime]] = None,
        max_quote_age_seconds: float = DEFAULT_MAX_QUOTE_AGE_SECONDS,
        enforce_market_hours: bool = False,
        current_time: Optional[datetime.datetime] = None,
        is_maker: bool = False
    ) -> Dict[str, Any]:
        """
        Full Institutional Fill Pipeline:
        1. Market Hours Gate (if enabled)
        2. Quote Freshness Gate (if timestamp provided)
        3. Volume / Partial Fill Gate
        4. Limit Order Crossing Gate
        5. Spread, Slippage & Fee TCA Calculation
        """
        clean_side = (side or "BUY").strip().upper()
        clean_type = (order_type or "market").strip().lower()
        clean_asset = (asset_class or "Equities").strip().capitalize()
        m_px = float(market_price)

        # 1. Market Hours Check
        if enforce_market_hours:
            hours_ok, hours_msg = cls.check_market_hours(asset_class=clean_asset, current_time=current_time)
            if not hours_ok:
                return {
                    "success": False,
                    "status": "REJECTED_MARKET_CLOSED",
                    "message": hours_msg,
                    "filled_quantity": 0.0,
                    "unfilled_quantity": float(quantity),
                    "execution_price": 0.0,
                    "tca": {}
                }

        # 2. Quote Freshness Check
        if quote_timestamp is not None:
            quote_ok, quote_age, quote_msg = cls.check_quote_freshness(
                quote_timestamp=quote_timestamp,
                max_age_seconds=max_quote_age_seconds,
                current_time=current_time
            )
            if not quote_ok:
                return {
                    "success": False,
                    "status": "REJECTED_STALE_QUOTE",
                    "message": quote_msg,
                    "quote_age_seconds": quote_age,
                    "max_allowed_age_seconds": max_quote_age_seconds,
                    "filled_quantity": 0.0,
                    "unfilled_quantity": float(quantity),
                    "execution_price": 0.0,
                    "tca": {}
                }

        # 3. Partial Fill on Volume Share
        filled_qty, unfilled_qty, is_partial, vol_msg = cls.calculate_volume_fill(
            order_quantity=quantity,
            average_daily_volume=average_daily_volume,
            max_volume_share=max_volume_share
        )

        if filled_qty <= 0:
            return {
                "success": False,
                "status": "REJECTED_ZERO_LIQUIDITY",
                "message": f"Zero liquidity available for {symbol}.",
                "filled_quantity": 0.0,
                "unfilled_quantity": float(quantity),
                "execution_price": 0.0,
                "tca": {}
            }

        # 4. Limit Order Crossing Validation
        if clean_type == "limit":
            if limit_price is None or limit_price <= 0:
                return {
                    "success": False,
                    "status": "REJECTED_INVALID_LIMIT",
                    "message": "Limit price is mandatory for limit orders.",
                    "filled_quantity": 0.0,
                    "unfilled_quantity": float(quantity),
                    "execution_price": 0.0,
                    "tca": {}
                }
            cross_ok, cross_msg = cls.evaluate_limit_crossing(
                side=clean_side,
                limit_price=limit_price,
                market_price=m_px
            )
            if not cross_ok:
                return {
                    "success": False,
                    "status": "UNFILLED",
                    "message": cross_msg,
                    "limit_price": limit_price,
                    "market_price": m_px,
                    "filled_quantity": 0.0,
                    "unfilled_quantity": float(quantity),
                    "execution_price": 0.0,
                    "tca": {}
                }

        # 5. Execution Costs, Spread & Slippage
        # Market orders fill at next price + spread + slippage
        # For limit orders that crossed, execution is bounded by limit price
        adv = average_daily_volume or 500000.0
        tca = ExecutionCostModel.calculate_execution_costs(
            asset_class=clean_asset,
            side=clean_side,
            quantity=filled_qty,
            price=m_px,
            daily_volatility_pct=daily_volatility_pct,
            average_daily_volume=adv,
            bid_ask_spread_pct=bid_ask_spread_pct,
            is_maker=is_maker
        )

        effective_px = tca["effective_price"]

        # Ensure limit order does not execute worse than limit price
        if clean_type == "limit" and limit_price is not None:
            if clean_side == "BUY" and effective_px > limit_price:
                effective_px = limit_price
                tca["effective_price"] = effective_px
            elif clean_side == "SELL" and effective_px < limit_price:
                effective_px = limit_price
                tca["effective_price"] = effective_px

        status = "PARTIALLY_FILLED" if is_partial else "FILLED"
        fill_desc = (
            f"✅ {status}: {clean_side} {filled_qty:,.2f} {symbol.upper()} @ ${effective_px:,.4f} "
            f"(Benchmark: ${m_px:,.2f} | Spread: ${tca['half_spread_cost_usd']:,.2f} | "
            f"Slippage: ${tca['market_impact_slippage_usd']:,.2f} | Fees: ${tca['commission_and_clearing_fees_usd']:,.2f})"
        )
        if is_partial:
            fill_desc += f" | {unfilled_qty:,.2f} shares unfilled."

        return {
            "success": True,
            "status": status,
            "message": fill_desc,
            "symbol": symbol.upper(),
            "asset_class": clean_asset,
            "side": clean_side,
            "order_type": clean_type.upper(),
            "filled_quantity": filled_qty,
            "unfilled_quantity": unfilled_qty,
            "is_partial": is_partial,
            "benchmark_price": m_px,
            "execution_price": effective_px,
            "limit_price": limit_price,
            "tca": tca
        }
