"""
Calculation Toolkit: Currency Conversion with Timestamp & Source Tracking
"""

from typing import Dict, Any, Optional
import datetime
import yfinance as yf

def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    custom_rate: Optional[float] = None,
    rate_date: Optional[str] = None
) -> Dict[str, Any]:
    """Convert an amount from one currency to another, displaying the exact quote rate, source, and quote date.
    
    If custom_rate is provided, rate_date must also be explicitly specified.
    If custom_rate is None, fetches the latest quote from Yahoo Finance and records the exact quote bar date.
    """
    from_curr = from_currency.upper().strip()
    to_curr = to_currency.upper().strip()
    
    # Handle GBp / GBX (Pence Sterling) vs GBP (Pounds)
    adjusted_amount = amount
    prefix_note = ""
    if from_curr in ("GBP_PENCE", "GBX", "GBP"):
        if from_currency in ("GBp", "GBX", "GBP_PENCE"):
            adjusted_amount = amount / 100.0
            from_curr = "GBP"
            prefix_note = f" (Converted {amount:,.2f} Pence to {adjusted_amount:,.2f} GBP)"
        
    if from_curr == to_curr:
        return {
            "result": adjusted_amount,
            "rate": 1.0,
            "rate_date": rate_date or "Same Currency",
            "source": "Identity (1:1)",
            "formula": f"amount * 1.0{prefix_note}",
            "inputs": {"amount": amount, "from_currency": from_currency, "to_currency": to_currency},
            "formatted": f"{adjusted_amount:,.2f} {to_curr}"
        }
        
    if custom_rate is not None:
        if not rate_date:
            raise ValueError("rate_date must be explicitly specified when providing a custom_rate.")
        effective_rate = float(custom_rate)
        effective_date = rate_date
        source = "Custom Input"
    else:
        # Fetch live quote date from Yahoo Finance
        pair = f"{from_curr}{to_curr}=X"
        effective_rate = None
        effective_date = None
        source = None
        
        try:
            ticker = yf.Ticker(pair)
            hist = ticker.history(period="5d")
            if not hist.empty:
                effective_rate = float(hist["Close"].iloc[-1])
                # Actual quote date from market data index
                effective_date = hist.index[-1].strftime("%Y-%m-%d")
                source = f"Yahoo Finance ({pair} market quote)"
            else:
                inv_pair = f"{to_curr}{from_curr}=X"
                inv_ticker = yf.Ticker(inv_pair)
                inv_hist = inv_ticker.history(period="5d")
                if not inv_hist.empty:
                    effective_rate = 1.0 / float(inv_hist["Close"].iloc[-1])
                    effective_date = inv_hist.index[-1].strftime("%Y-%m-%d")
                    source = f"Yahoo Finance (Derived 1 / {inv_pair} market quote)"
        except Exception as e:
            raise ValueError(f"Could not fetch market FX quote for {from_curr}->{to_curr}: {e}. Provide custom_rate and rate_date.")
            
        if effective_rate is None or effective_date is None:
            raise ValueError(f"No market quote found for {from_curr} to {to_curr}.")
        
    converted_amount = adjusted_amount * effective_rate
    
    return {
        "result": converted_amount,
        "rate": effective_rate,
        "rate_date": effective_date,
        "source": source,
        "formula": f"amount ({adjusted_amount:,.2f} {from_curr}) * exchange_rate ({effective_rate:.4f}){prefix_note}",
        "inputs": {
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": effective_rate,
            "quote_date": effective_date
        },
        "formatted": f"{converted_amount:,.2f} {to_curr} (Rate: 1 {from_curr} = {effective_rate:.4f} {to_curr}, Quote Date: {effective_date}, Source: {source})"
    }
