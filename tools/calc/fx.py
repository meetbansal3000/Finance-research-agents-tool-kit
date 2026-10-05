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
    """Convert an amount from one currency to another, displaying the exact FX rate, source, and date.
    
    If custom_rate is not provided, fetches current spot rate from Yahoo Finance (e.g., GBPUSD=X, USDINR=X).
    """
    from_curr = from_currency.upper().strip()
    to_curr = to_currency.upper().strip()
    
    # Handle GBp / GBX (Pence Sterling) vs GBP (Pounds)
    adjusted_amount = amount
    prefix_note = ""
    if from_curr in ("GBP_PENCE", "GBX", "GBp".upper()):
        adjusted_amount = amount / 100.0
        from_curr = "GBP"
        prefix_note = f" (Converted {amount:,.2f} Pence to {adjusted_amount:,.2f} GBP)"
        
    if from_curr == to_curr:
        return {
            "result": adjusted_amount,
            "rate": 1.0,
            "rate_date": rate_date or datetime.date.today().isoformat(),
            "source": "Identity (1:1)",
            "formula": f"amount * 1.0{prefix_note}",
            "inputs": {"amount": amount, "from_currency": from_currency, "to_currency": to_currency},
            "formatted": f"{adjusted_amount:,.2f} {to_curr}"
        }
        
    effective_rate = custom_rate
    effective_date = rate_date
    source = "Custom Input"
    
    if effective_rate is None:
        pair = f"{from_curr}{to_curr}=X"
        try:
            ticker = yf.Ticker(pair)
            hist = ticker.history(period="5d")
            if not hist.empty:
                effective_rate = float(hist["Close"].iloc[-1])
                effective_date = hist.index[-1].strftime("%Y-%m-%d")
                source = f"Yahoo Finance ({pair})"
            else:
                inv_pair = f"{to_curr}{from_curr}=X"
                inv_ticker = yf.Ticker(inv_pair)
                inv_hist = inv_ticker.history(period="5d")
                if not inv_hist.empty:
                    effective_rate = 1.0 / float(inv_hist["Close"].iloc[-1])
                    effective_date = inv_hist.index[-1].strftime("%Y-%m-%d")
                    source = f"Yahoo Finance (Derived 1 / {inv_pair})"
        except Exception as e:
            raise ValueError(f"Could not automatically fetch FX rate for {from_curr}->{to_curr}: {e}. Provide custom_rate.")
            
    if effective_rate is None:
        raise ValueError(f"No exchange rate found for {from_curr} to {to_curr}.")
        
    converted_amount = adjusted_amount * effective_rate
    
    return {
        "result": converted_amount,
        "rate": effective_rate,
        "rate_date": effective_date or datetime.date.today().isoformat(),
        "source": source,
        "formula": f"amount ({adjusted_amount:,.2f} {from_curr}) * exchange_rate ({effective_rate:.4f}){prefix_note}",
        "inputs": {
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": effective_rate
        },
        "formatted": f"{converted_amount:,.2f} {to_curr} (Rate: 1 {from_curr} = {effective_rate:.4f} {to_curr}, Date: {effective_date}, Source: {source})"
    }
