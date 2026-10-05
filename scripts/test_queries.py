"""
Verification test script for Open Source Stock and Market Research Toolkit
Queries:
1. Apple Inc. (AAPL) last 4 quarters of revenue from SEC Filings with accession numbers and URLs.
2. Microsoft Corp. (MSFT) current price and 1-year historical price data via OpenBB / yfinance.
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Load .env configuration
load_dotenv()

def run_apple_sec_revenue_query():
    print("=" * 80)
    print("QUERY 1: Apple Inc. (AAPL) Last 4 Quarters of Revenue from SEC Filings")
    print("=" * 80)
    
    from edgar import set_identity, Company
    
    identity = os.getenv("EDGAR_IDENTITY", "Research Analyst research.analyst@example.com")
    set_identity(identity)
    
    company = Company("AAPL")
    print(f"Company: {company.name} | CIK: {company.cik}")
    
    # Retrieve facts from SEC XBRL data
    facts = company.get_facts()
    df = facts.to_dataframe()
    
    # Filter for revenue concept and quarterly duration (~90 days)
    rev = df[(df['concept'] == 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax') & (df['period_type'] == 'duration')].copy()
    rev['duration_days'] = (pd.to_datetime(rev['period_end']) - pd.to_datetime(rev['period_start'])).dt.days
    quarterly = rev[(rev['duration_days'] >= 75) & (rev['duration_days'] <= 105)].sort_values(by='period_end', ascending=False).drop_duplicates(subset=['period_end'])
    
    recent_4q = quarterly.head(4)
    print("\n--- Apple (AAPL) Last 4 Quarters Revenue (Source: SEC EDGAR Filings) ---")
    for idx, row in recent_4q.iterrows():
        fiscal = f"FY{row['fiscal_year']} {row['fiscal_period']}"
        period = f"{row['period_start']} to {row['period_end']}"
        rev_usd = row['numeric_value']
        print(f"• {fiscal} ({period}): ${rev_usd:,.2f} ({rev_usd/1e9:.2f} Billion USD)")
        
    print(f"\nSEC Filing CIK Directory URL: https://www.sec.gov/edgar/browse/?CIK=0000320193")
    return recent_4q

def run_msft_openbb_query():
    print("\n" + "=" * 80)
    print("QUERY 2: Microsoft Corp. (MSFT) Current Price & 1-Year History (OpenBB / yfinance)")
    print("=" * 80)
    
    from openbb import obb
    
    # Query 1-year historical data
    hist_result = obb.yfinance.equity.price.historical(symbol="MSFT")
    df_hist = hist_result.to_dataframe()
    
    print(f"Retrieved {len(df_hist)} trading days of historical data.")
    print(f"1-Year Range: {df_hist.index[0]} to {df_hist.index[-1]}")
    
    latest_close = df_hist['close'].iloc[-1]
    latest_date = df_hist.index[-1]
    high_52w = df_hist['high'].max()
    low_52w = df_hist['low'].min()
    
    print(f"\n• MSFT Latest Close: ${latest_close:.2f} (Date: {latest_date})")
    print(f"• 52-Week High: ${high_52w:.2f}")
    print(f"• 52-Week Low:  ${low_52w:.2f}")
    
    print("\nRecent 5 Trading Days:")
    print(df_hist[['open', 'high', 'low', 'close', 'volume']].tail(5))
    print("\nData Source Endpoint: OpenBB Platform yfinance provider (obb.yfinance.equity.price.historical)")

if __name__ == "__main__":
    run_apple_sec_revenue_query()
    run_msft_openbb_query()
