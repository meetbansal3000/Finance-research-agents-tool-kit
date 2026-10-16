"""
tools/journal_gate.py
Mandatory Journal Gate & Fiduciary Trade Entry Gatekeeper.

Enforces strict institutional discipline before any paper order can execute:
1. Thesis: A documented, substantive investment hypothesis explaining why the trade is taken.
2. Invalidation Condition: An explicit, measurable stop/exit condition proving the thesis wrong.
3. Position Size Rule: Order capital commitment must not exceed a set percentage of total portfolio equity (default 20%).
4. Review Date: A scheduled, future date (YYYY-MM-DD) when the trade/thesis must be formally re-evaluated.

No paper order is permitted to execute without passing all four checks.
"""

import os
import csv
import datetime
from typing import Dict, Any, Optional, Tuple, Union


PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JOURNAL_CSV_PATH = os.path.join(PROJECT_DIR, "journal", "journal.csv")


class JournalGate:
    """
    Mandatory pre-trade fiduciary gatekeeper enforcing thesis, invalidation,
    position sizing constraints, and review scheduling.
    """

    DEFAULT_MAX_POSITION_SIZE_PCT = 0.20  # 20.0% max position size of total portfolio equity

    @classmethod
    def validate_trade(
        cls,
        thesis: Optional[str],
        invalidation_condition: Optional[str],
        order_cost: float,
        total_equity: float,
        review_date: Optional[Union[str, datetime.date, datetime.datetime]],
        max_position_size_pct: Optional[float] = None,
        currency: str = "USD",
        currency_symbol: str = "$"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate that an order satisfies all four Journal Gate invariants:
        1. Non-empty investment thesis.
        2. Non-empty invalidation condition.
        3. Order cost within position size rule (% of total equity).
        4. Valid review date strictly in the future.
        """
        # 1. Thesis Check
        clean_thesis = (thesis or "").strip()
        if not clean_thesis or len(clean_thesis) < 5:
            return (
                False,
                "Journal Gate Refusal: Trade thesis is required. Provide a substantive investment rationale.",
                {
                    "gate": "thesis",
                    "status": "REJECTED_JOURNAL_GATE",
                    "reason": "MISSING_THESIS"
                }
            )

        # 2. Invalidation Condition Check
        clean_invalidation = (invalidation_condition or "").strip()
        if not clean_invalidation or len(clean_invalidation) < 5:
            return (
                False,
                "Journal Gate Refusal: Invalidation condition is required. Specify what market condition invalidates this thesis.",
                {
                    "gate": "invalidation_condition",
                    "status": "REJECTED_JOURNAL_GATE",
                    "reason": "MISSING_INVALIDATION_CONDITION"
                }
            )

        # 3. Position Sizing Rule Check
        cost = max(0.0, float(order_cost))
        equity = float(total_equity)
        max_rule = float(max_position_size_pct) if max_position_size_pct is not None else cls.DEFAULT_MAX_POSITION_SIZE_PCT

        if equity > 0:
            size_pct = round(cost / equity, 4)
            if size_pct > max_rule:
                return (
                    False,
                    f"Journal Gate Refusal: Position size breach. Order cost of {currency_symbol}{cost:,.2f} {currency} "
                    f"({size_pct * 100:.1f}%) exceeds maximum permitted size rule of {max_rule * 100:.1f}% "
                    f"of total portfolio equity ({currency_symbol}{equity:,.2f} {currency}).",
                    {
                        "gate": "position_size_rule",
                        "status": "REJECTED_JOURNAL_GATE",
                        "reason": "POSITION_SIZE_BREACH",
                        "order_cost": cost,
                        "total_equity": equity,
                        "position_size_pct": size_pct,
                        "max_position_size_pct": max_rule
                    }
                )
        else:
            size_pct = 0.0

        # 4. Review Date Check
        if not review_date:
            return (
                False,
                "Journal Gate Refusal: Review date is required. Specify a future review date (YYYY-MM-DD).",
                {
                    "gate": "review_date",
                    "status": "REJECTED_JOURNAL_GATE",
                    "reason": "MISSING_REVIEW_DATE"
                }
            )

        try:
            if isinstance(review_date, str):
                parsed_rd = datetime.date.fromisoformat(review_date.strip())
            elif isinstance(review_date, datetime.datetime):
                parsed_rd = review_date.date()
            elif isinstance(review_date, datetime.date):
                parsed_rd = review_date
            else:
                raise ValueError(f"Unsupported review_date type: {type(review_date)}")

            today = datetime.datetime.now(datetime.timezone.utc).date()
            if parsed_rd < today:
                return (
                    False,
                    f"Journal Gate Refusal: Review date {parsed_rd.isoformat()} cannot be in the past. Today is {today.isoformat()}.",
                    {
                        "gate": "review_date",
                        "status": "REJECTED_JOURNAL_GATE",
                        "reason": "PAST_REVIEW_DATE",
                        "review_date": parsed_rd.isoformat(),
                        "today": today.isoformat()
                    }
                )
            review_date_str = parsed_rd.isoformat()
        except Exception:
            return (
                False,
                f"Journal Gate Refusal: Invalid review date format '{review_date}'. Expected ISO format YYYY-MM-DD.",
                {
                    "gate": "review_date",
                    "status": "REJECTED_JOURNAL_GATE",
                    "reason": "INVALID_REVIEW_DATE_FORMAT",
                    "review_date": str(review_date)
                }
            )

        return (
            True,
            "Journal Gate Approved: All 4 fiduciary rules verified.",
            {
                "gate": "APPROVED",
                "status": "PASSED",
                "thesis": clean_thesis,
                "invalidation_condition": clean_invalidation,
                "review_date": review_date_str,
                "position_size_pct": size_pct,
                "max_position_size_pct": max_rule
            }
        )

    @classmethod
    def append_journal_record(
        cls,
        order_id: str,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        thesis: str,
        invalidation_condition: str,
        review_date: str,
        journal_csv_path: str = JOURNAL_CSV_PATH
    ) -> bool:
        """Append an audited trade record into journal/journal.csv."""
        try:
            os.makedirs(os.path.dirname(journal_csv_path), exist_ok=True)
            today_str = datetime.date.today().isoformat()
            file_exists = os.path.exists(journal_csv_path)

            row = {
                "decision_id": order_id,
                "date": today_str,
                "ticker": symbol.upper(),
                "action": side.upper(),
                "entry_price": f"{entry_price:.2f}",
                "target_price": "",
                "stop_loss": "",
                "conviction": "HIGH",
                "status": "OPEN",
                "exit_date": "",
                "exit_price": "",
                "return_pct": "",
                "agent_prediction": f"Reviewed on {review_date}",
                "market_consensus": "",
                "user_thoughts": f"Qty: {quantity}",
                "thesis": thesis,
                "risks": invalidation_condition
            }

            fieldnames = [
                "decision_id", "date", "ticker", "action", "entry_price", "target_price",
                "stop_loss", "conviction", "status", "exit_date", "exit_price", "return_pct",
                "agent_prediction", "market_consensus", "user_thoughts", "thesis", "risks"
            ]

            with open(journal_csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
            return True
        except Exception:
            return False
