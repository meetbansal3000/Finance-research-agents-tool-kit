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
    """Convert an amount from one currency to another, displaying the exact FX rate and date.
    
    If custom_rate is not provided, fetches current spot rate from yfinance (e.g., GBPUSD=X, USDINR=X).
    """
    from_curr = from_currency.upper().strip()
    to_curr = to_currency.upper().strip()
    
    # Handle GBp (pence) vs GBP (pounds)
    pence_multiplier = 1.0
    if from_curr == "GBP" or from_curr == "GBP":
        pass
    elif from_curr == "GBX" or from_curr == "GBP":
        # 100 pence = 1 pound
        pence_multiplier = 0.01
        
    if from_curr == to_curr:
        return {
            "result": amount,
            "formula": "amount * 1.0 (Identical currencies)",
            "rate": 1.0,
            "rate_date": rate_date or datetime.date.today().isoformat(),
            "inputs": {"amount": amount, "from_currency": from_currency, "to_currency": to_currency},
            "formatted": f"{amount:,.2f} {to_curr}"
        }
        
    effective_rate = custom_rate
    effective_date = rate_date
    source = "Custom Input"
    
    if effective_rate is None:
        # Standard FX pair ticker on Yahoo Finance
        pair = f"{from_curr}{to_curr}=X"
        try:
            ticker = yf.Ticker(pair)
            hist = ticker.history(period="5d")
            if not hist.empty:
                effective_rate = float(hist["Close"].iloc[-1])
                effective_date = hist.index[-1].strftime("%Y-%m-%d")
                source = f"Yahoo Finance ({pair})"
            else:
                # Try inverse pair
                inv_pair = f"{to_curr}{from_curr}=X"
                inv_ticker = yf.Ticker(inv_pair)
                inv_hist = inv_ticker.history(period="5d")
                if not inv_hist.empty:
                    effective_rate = 1.0 / float(inv_hist["Close"].iloc[-1])
                    effective_date = inv_hist.index[-1].strftime("%Y-%m-%d")
                    source = f"Yahoo Finance (1 / {inv_pair})"
        except Exception as e:
            raise ValueError(f"Could not automatically fetch FX rate for {from_curr}->{to_curr}: {e}. Provide custom_rate.")
            
    if effective_rate is None:
        raise ValueError(f"No exchange rate found for {from_curr} to {to_curr}.")
        
    converted_amount = amount * effective_rate
    
    return {
        "result": converted_amount,
        "rate": effective_rate,
        "rate_date": effective_date or datetime.date.today().isoformat(),
        "source": source,
        "formula": f"amount ({amount:,.2f} {from_curr}) * exchange_rate ({effective_rate:.4f})",
        "inputs": {
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": effective_rate
        },
        "formatted": f"{converted_amount:,.2f} {to_curr} (Rate: 1 {from_curr} = {effective_rate:.4f} {to_curr}, Date: {effective_date})"
    }
