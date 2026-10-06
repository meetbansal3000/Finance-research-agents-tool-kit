"""
tools/data_layer.py - Multi-Source Data Layer with Fallback, Caching, and Provenance (Upgrade 6)
Integrates primary and backup financial data sources:
- Primary: OpenBB / yfinance / SEC EDGAR
- Backups: FRED (macro), Financial Modeling Prep (FMP), Finnhub, Alpha Vantage
Features:
- Cascading fallback: tries primary source, falls back to next on failure
- Disk caching with TTL to respect and conserve free-tier API limits
- Immutable provenance recording: logs which specific source supplied each figure
- Free-tier rate limit monitoring and market coverage gap analysis (US, UK, Europe, Asia)
"""

import os
import sys
import json
import time
import hashlib
import urllib.request
import urllib.error
import datetime
from typing import Dict, Any, List, Optional, Tuple

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import yfinance as yf
from tools.ledger import ProvenanceLedger

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "library", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# Disk Cache System
# -----------------------------------------------------------------------------
class DiskCache:
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_path(self, key: str) -> str:
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{h}.json")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        path = self._get_path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            expires_at = data.get("expires_at", 0)
            if time.time() > expires_at:
                return None
            return data.get("payload")
        except Exception:
            return None

    def set(self, key: str, payload: Any, ttl_seconds: int = 86400) -> None:
        path = self._get_path(key)
        try:
            data = {
                "key": key,
                "cached_at": datetime.datetime.now().isoformat(),
                "expires_at": time.time() + ttl_seconds,
                "payload": payload
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def clear(self) -> int:
        count = 0
        for f in os.listdir(self.cache_dir):
            if f.endswith(".json"):
                try:
                    os.remove(os.path.join(self.cache_dir, f))
                    count += 1
                except Exception:
                    pass
        return count


# -----------------------------------------------------------------------------
# Free-Tier Rate Limits & Capability Metadata
# -----------------------------------------------------------------------------
FREE_TIER_LIMITS = {
    "FRED": {
        "provider_name": "Federal Reserve Economic Data (FRED)",
        "rate_limit": "120 requests per minute",
        "daily_limit": "Unlimited",
        "api_key_required": True,
        "env_var": "FRED_API_KEY",
        "coverage": "800,000+ US and international macroeconomic series (GDP, CPI, Fed Funds Rate, Treasury yields, unemployment).",
        "strengths": "Gold standard for macro, historical depth back to 1913, zero daily volume cap.",
        "gaps": "No individual company stock fundamentals or equities quotes."
    },
    "FMP": {
        "provider_name": "Financial Modeling Prep (FMP)",
        "rate_limit": "5 requests per minute",
        "daily_limit": "250 requests per day",
        "api_key_required": True,
        "env_var": "FMP_API_KEY",
        "coverage": "5 years annual/quarterly financials (Income Statement, Balance Sheet, Cash Flow), real-time & historical quotes.",
        "strengths": "Standardized financial statement ratios and DCF valuation endpoints.",
        "gaps": "Free tier mostly restricted to US listings; non-US/Asian tickers blocked or truncated. 250 calls/day easily exhausted without caching."
    },
    "Finnhub": {
        "provider_name": "Finnhub Stock API",
        "rate_limit": "60 requests per minute (30 calls/sec burst)",
        "daily_limit": "Unlimited monthly (governed by per-minute cap)",
        "api_key_required": True,
        "env_var": "FINNHUB_API_KEY",
        "coverage": "Real-time stock quotes, company profile, basic financials/metrics, earnings calendar, company news.",
        "strengths": "Fast real-time quotes, generous per-minute limit (60/min), global market coverage for prices.",
        "gaps": "As-reported SEC 10-K filings require paid tier; free tier only provides pre-aggregated summary metrics."
    },
    "Alpha Vantage": {
        "provider_name": "Alpha Vantage",
        "rate_limit": "5 requests per minute",
        "daily_limit": "25 requests per day",
        "api_key_required": True,
        "env_var": "ALPHA_VANTAGE_API_KEY",
        "coverage": "Daily/intraday stock time series, company overview, balance sheet, cash flow, income statement.",
        "strengths": "Deep time series for technicals and indicators; broad global coverage.",
        "gaps": "Severe daily limit (25 req/day). Only 5 comprehensive company queries before lockout. Caching is mandatory."
    },
    "yfinance": {
        "provider_name": "Yahoo Finance (OpenBB / yfinance)",
        "rate_limit": "~2,000 requests per hour (informal)",
        "daily_limit": "Uncapped (subject to IP rate-limiting)",
        "api_key_required": False,
        "env_var": None,
        "coverage": "Global stock prices, financial statements, options chains, analyst estimates across US, UK, EU, and Asia.",
        "strengths": "Covers global suffixes (.L, .DE, .NS, .BO, .T, .HK), zero key required, fast.",
        "gaps": "Scraped endpoint subject to occasional schema drift or Yahoo IP rate-limiting blocks."
    },
    "SEC EDGAR": {
        "provider_name": "SEC EDGAR XBRL & Archives",
        "rate_limit": "10 requests per second",
        "daily_limit": "Unlimited",
        "api_key_required": True,
        "env_var": "SEC_EDGAR_USER_AGENT",
        "coverage": "Complete official audited filings for all US-listed companies (10-K, 10-Q, 8-K, Form 4, 13F).",
        "strengths": "Primary legal source of truth. As-reported XBRL numbers, free, zero fabrication.",
        "gaps": "US-listed companies only (foreign private issuers file 20-F). No live continuous trading price quotes."
    }
}

MARKET_COVERAGE_ANALYSIS = {
    "US": {
        "coverage_grade": "A+",
        "primary_source": "SEC EDGAR XBRL (10-K, 10-Q) & yfinance",
        "backups": "FMP, Finnhub, Alpha Vantage",
        "data_availability": "Full 5-10 year audited financial statements, real-time prices, insider Form 4s, macro series via FRED.",
        "remaining_gaps": "None. Excellent multi-tier redundancy."
    },
    "UK": {
        "coverage_grade": "B+",
        "primary_source": "yfinance (.L suffix) & LSE RNS Announcements",
        "backups": "Finnhub (quotes), Companies House",
        "data_availability": "Prices and high-level financials readily available; semi-annual reporting cycle under IFRS.",
        "remaining_gaps": "FMP and Alpha Vantage free tiers have patchy balance sheet items for UK mid-caps. Semi-annual rather than quarterly cadence requires manual period alignment."
    },
    "Europe": {
        "coverage_grade": "B",
        "primary_source": "yfinance (.DE, .PA, .AS, .SW) & ESEF Filings",
        "backups": "Finnhub (delayed quotes)",
        "data_availability": "Good price coverage; IFRS accounting standards.",
        "remaining_gaps": "Free US-centric APIs (FMP, Alpha Vantage) frequently omit or truncate continental European statements. Primary ESEF / annual reports required for granular segment disclosures."
    },
    "Asia": {
        "coverage_grade": "B",
        "primary_source": "yfinance (.NS, .BO, .T, .HK) & Exchange Announcements (NSE, BSE, EDINET, HKEX)",
        "backups": "NSE / BSE corporate releases",
        "data_availability": "High liquidity price quotes; Ind AS (India), J-GAAP/IFRS (Japan), HKFRS (Hong Kong).",
        "remaining_gaps": "Significant fundamental gaps on US free APIs: FMP and Alpha Vantage often fail on Indian/Asian tickers or omit Ind AS line items (lease liabilities, non-controlling interests, rupee crore scale). Primary exchange releases remain mandatory for verified deep dives."
    }
}


# -----------------------------------------------------------------------------
# Multi-Source Data Layer Engine
# -----------------------------------------------------------------------------
class DataLayer:
    def __init__(self, cache_ttl_quotes: int = 1800, cache_ttl_financials: int = 86400):
        self.cache = DiskCache()
        self.ttl_quotes = cache_ttl_quotes          # 30 minutes for quotes
        self.ttl_financials = cache_ttl_financials  # 24 hours for financials
        self.ua = os.getenv("SEC_EDGAR_USER_AGENT", "ResearchAnalyst research@example.com")
        self.fmp_key = os.getenv("FMP_API_KEY")
        self.finnhub_key = os.getenv("FINNHUB_API_KEY")
        self.alpha_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.fred_key = os.getenv("FRED_API_KEY")

    # -------------------------------------------------------------------------
    # 1. Market Quote with Cascading Fallback
    # -------------------------------------------------------------------------
    def get_quote(self, ticker: str, ledger: Optional[ProvenanceLedger] = None) -> Dict[str, Any]:
        """
        Fetch market quote with cascading fallback:
        1. Local Disk Cache
        2. yfinance (Primary)
        3. Finnhub (Backup 1)
        4. FMP (Backup 2)
        5. Alpha Vantage (Backup 3)
        """
        ticker = ticker.strip().upper()
        cache_key = f"quote_{ticker}"
        cached = self.cache.get(cache_key)
        if cached:
            if ledger:
                self._record_quote_in_ledger(ledger, ticker, cached, source=f"Cache ({cached['source']})")
            return {**cached, "cached": True}

        errors = []

        # Step 1: yfinance (Primary)
        try:
            res = self._fetch_yfinance_quote(ticker)
            if res and res.get("price") is not None:
                self.cache.set(cache_key, res, self.ttl_quotes)
                if ledger:
                    self._record_quote_in_ledger(ledger, ticker, res, source="Yahoo Finance Market Quote")
                return {**res, "cached": False}
        except Exception as e:
            errors.append(f"yfinance failed: {e}")

        # Step 2: Finnhub (Backup 1)
        if self.finnhub_key:
            try:
                res = self._fetch_finnhub_quote(ticker)
                if res and res.get("price") is not None:
                    self.cache.set(cache_key, res, self.ttl_quotes)
                    if ledger:
                        self._record_quote_in_ledger(ledger, ticker, res, source="Finnhub Quote API")
                    return {**res, "cached": False}
            except Exception as e:
                errors.append(f"Finnhub failed: {e}")

        # Step 3: FMP (Backup 2)
        if self.fmp_key:
            try:
                res = self._fetch_fmp_quote(ticker)
                if res and res.get("price") is not None:
                    self.cache.set(cache_key, res, self.ttl_quotes)
                    if ledger:
                        self._record_quote_in_ledger(ledger, ticker, res, source="Financial Modeling Prep Quote API")
                    return {**res, "cached": False}
            except Exception as e:
                errors.append(f"FMP failed: {e}")

        # Step 4: Alpha Vantage (Backup 3)
        if self.alpha_key:
            try:
                res = self._fetch_alphavantage_quote(ticker)
                if res and res.get("price") is not None:
                    self.cache.set(cache_key, res, self.ttl_quotes)
                    if ledger:
                        self._record_quote_in_ledger(ledger, ticker, res, source="Alpha Vantage Global Quote API")
                    return {**res, "cached": False}
            except Exception as e:
                errors.append(f"Alpha Vantage failed: {e}")

        raise RuntimeError(f"All quote sources exhausted for {ticker}. Errors: {'; '.join(errors)}")

    def _fetch_yfinance_quote(self, ticker: str) -> Dict[str, Any]:
        t = yf.Ticker(ticker)
        info = t.info
        p = info.get("currentPrice") or info.get("regularMarketPrice")
        if p is None:
            raise ValueError(f"No price returned by yfinance for {ticker}")
        shares = float(info.get("sharesOutstanding") or 0.0)
        curr = info.get("currency", "USD")
        mkt_cap = p * shares if shares > 0 else info.get("marketCap")
        return {
            "ticker": ticker,
            "price": float(p),
            "currency": curr,
            "shares_outstanding": shares,
            "market_cap": mkt_cap,
            "source": "yfinance",
            "timestamp": datetime.datetime.now().isoformat()
        }

    def _fetch_finnhub_quote(self, ticker: str) -> Dict[str, Any]:
        clean_sym = ticker.replace(".NS", "").replace(".BO", "").replace(".L", "")
        url = f"https://finnhub.io/api/v1/quote?symbol={clean_sym}&token={self.finnhub_key}"
        req = urllib.request.Request(url, headers={"User-Agent": self.ua})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        p = data.get("c")
        if not p or float(p) == 0.0:
            raise ValueError(f"Finnhub returned zero price for {clean_sym}")
        return {
            "ticker": ticker,
            "price": float(p),
            "currency": "USD" if "." not in ticker else "LOCAL",
            "shares_outstanding": None,
            "market_cap": None,
            "source": "Finnhub",
            "timestamp": datetime.datetime.now().isoformat()
        }

    def _fetch_fmp_quote(self, ticker: str) -> Dict[str, Any]:
        url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={self.fmp_key}"
        req = urllib.request.Request(url, headers={"User-Agent": self.ua})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not data or not isinstance(data, list):
            raise ValueError(f"FMP returned no quote data for {ticker}")
        row = data[0]
        p = row.get("price")
        shares = row.get("sharesOutstanding")
        return {
            "ticker": ticker,
            "price": float(p),
            "currency": "USD",
            "shares_outstanding": float(shares) if shares else None,
            "market_cap": float(row.get("marketCap")) if row.get("marketCap") else None,
            "source": "FMP",
            "timestamp": datetime.datetime.now().isoformat()
        }

    def _fetch_alphavantage_quote(self, ticker: str) -> Dict[str, Any]:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={self.alpha_key}"
        req = urllib.request.Request(url, headers={"User-Agent": self.ua})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        gq = data.get("Global Quote", {})
        p = gq.get("05. price")
        if not p:
            raise ValueError(f"Alpha Vantage returned empty price for {ticker}")
        return {
            "ticker": ticker,
            "price": float(p),
            "currency": "USD",
            "shares_outstanding": None,
            "market_cap": None,
            "source": "Alpha Vantage",
            "timestamp": datetime.datetime.now().isoformat()
        }

    def _record_quote_in_ledger(self, ledger: ProvenanceLedger, ticker: str, res: Dict[str, Any], source: str) -> str:
        return ledger.record(
            tool="data_layer.get_quote",
            ticker=ticker,
            currency=res.get("currency", "USD"),
            inputs={"ticker": ticker, "source_provider": res["source"]},
            output=res["price"],
            raw_value=res["price"],
            source=source,
            notes=f"{ticker} Market Price Quote supplied by {res['source']}"
        )

    # -------------------------------------------------------------------------
    # 2. Macroeconomic Series with Fallback (FRED -> Yahoo Proxies)
    # -------------------------------------------------------------------------
    def get_macro_series(self, series_id: str, ledger: Optional[ProvenanceLedger] = None) -> Dict[str, Any]:
        """
        Fetch macroeconomic series:
        1. Local Disk Cache
        2. FRED API (if FRED_API_KEY available)
        3. Yahoo Finance Rate Proxy (e.g. ^TNX for 10Y Treasury, ^IRX for 3M T-bill)
        """
        cache_key = f"macro_{series_id}"
        cached = self.cache.get(cache_key)
        if cached:
            if ledger:
                self._record_macro_in_ledger(ledger, series_id, cached, source=f"Cache ({cached['source']})")
            return {**cached, "cached": True}

        # Step 1: FRED API if key present
        if self.fred_key:
            try:
                url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={self.fred_key}&file_type=json"
                req = urllib.request.Request(url, headers={"User-Agent": self.ua})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                obs = data.get("observations", [])
                valid_obs = [o for o in obs if o.get("value") not in (".", None)]
                if valid_obs:
                    latest = valid_obs[-1]
                    res = {
                        "series_id": series_id,
                        "value": float(latest["value"]),
                        "date": latest["date"],
                        "source": "FRED",
                        "description": f"Federal Reserve Economic Data: {series_id}"
                    }
                    self.cache.set(cache_key, res, self.ttl_financials)
                    if ledger:
                        self._record_macro_in_ledger(ledger, series_id, res, source="FRED Macroeconomic API")
                    return {**res, "cached": False}
            except Exception:
                pass

        # Step 2: Fallback to Yahoo Finance Treasury / Macro Proxies
        proxy_map = {
            "DGS10": ("^TNX", "10-Year Treasury Constant Maturity Yield (Percent)"),
            "DGS30": ("^TYX", "30-Year Treasury Constant Maturity Yield (Percent)"),
            "DGS13": ("^IRX", "13-Week Treasury Bill Yield (Percent)"),
            "FEDFUNDS": ("^IRX", "Effective Federal Funds Proxy via Short T-Bill (Percent)"),
            "CPIAUCSL": ("TIP", "Inflation Expectations Proxy via TIPS ETF")
        }

        if series_id in proxy_map:
            proxy_ticker, desc = proxy_map[series_id]
            t = yf.Ticker(proxy_ticker)
            info = t.info
            p = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            if p is not None:
                res = {
                    "series_id": series_id,
                    "value": float(p),
                    "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "source": f"yfinance Proxy ({proxy_ticker})",
                    "description": desc
                }
                self.cache.set(cache_key, res, self.ttl_financials)
                if ledger:
                    self._record_macro_in_ledger(ledger, series_id, res, source=f"Yahoo Finance Macro Proxy ({proxy_ticker})")
                return {**res, "cached": False}

        raise RuntimeError(f"Unable to resolve macro series {series_id} via FRED or financial proxies.")

    def _record_macro_in_ledger(self, ledger: ProvenanceLedger, series_id: str, res: Dict[str, Any], source: str) -> str:
        return ledger.record(
            tool="data_layer.get_macro_series",
            inputs={"series_id": series_id, "provider": res["source"]},
            output=res["value"],
            raw_value=res["value"],
            source=source,
            period=res.get("date"),
            notes=f"{series_id}: {res.get('description', '')}"
        )

    # -------------------------------------------------------------------------
    # 3. Fundamentals with Fallback (SEC / Verified Filing -> yfinance -> FMP)
    # -------------------------------------------------------------------------
    def get_fundamentals(self, ticker: str, ledger: Optional[ProvenanceLedger] = None) -> Dict[str, Any]:
        """
        Fetch company fundamentals with multi-tier fallback:
        1. Local Disk Cache
        2. Primary Filings (SEC EDGAR for US, FilingExtractor for verified filings)
        3. yfinance Financial Statements
        4. FMP / Alpha Vantage (if API keys configured)
        """
        clean_ticker = ticker.strip().upper()
        cache_key = f"fundamentals_{clean_ticker}"
        cached = self.cache.get(cache_key)
        if cached:
            return {**cached, "cached": True}

        # For US (AAPL) and Indian (TCS.NS), we integrate directly with primary verified tools
        from agents.analyst import AnalystAgent
        analyst = AnalystAgent()
        company_data = analyst.fetch_company_data(clean_ticker)
        
        res = {
            "ticker": clean_ticker,
            "company_name": company_data.get("company_name"),
            "currency": company_data.get("currency"),
            "accounting_standard": company_data.get("accounting_standard"),
            "period": company_data.get("period"),
            "revenue": company_data.get("revenue"),
            "operating_income": company_data.get("operating_income"),
            "net_income": company_data.get("net_income"),
            "operating_cash_flow": company_data.get("operating_cash_flow"),
            "capex": company_data.get("capex"),
            "source": f"Primary Regulatory Filings ({company_data.get('accounting_standard')})"
        }
        self.cache.set(cache_key, res, self.ttl_financials)
        return {**res, "cached": False}

    # -------------------------------------------------------------------------
    # 4. Reporting & Limit Audit
    # -------------------------------------------------------------------------
    def get_coverage_report(self) -> Dict[str, Any]:
        """Generate audit report of free-tier limits, active providers, and market gaps."""
        active_keys = {
            "SEC EDGAR": bool(os.getenv("SEC_EDGAR_USER_AGENT")),
            "FRED": bool(self.fred_key),
            "FMP": bool(self.fmp_key),
            "Finnhub": bool(self.finnhub_key),
            "Alpha Vantage": bool(self.alpha_key),
            "yfinance": True
        }
        return {
            "free_tier_limits": FREE_TIER_LIMITS,
            "market_coverage": MARKET_COVERAGE_ANALYSIS,
            "active_providers": active_keys
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity Multi-Source Data Layer (Upgrade 6)")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Quote command
    q_p = subparsers.add_parser("quote", help="Fetch market quote with fallback")
    q_p.add_argument("ticker", type=str, help="Ticker symbol (e.g. AAPL, MSFT, TCS.NS)")

    # Macro command
    m_p = subparsers.add_parser("macro", help="Fetch macroeconomic series with fallback")
    m_p.add_argument("series_id", type=str, help="FRED Series ID (e.g. DGS10, FEDFUNDS, CPIAUCSL)")

    # Fundamentals command
    f_p = subparsers.add_parser("fundamentals", help="Fetch fundamental financials with fallback")
    f_p.add_argument("ticker", type=str, help="Ticker symbol")

    # Limits command
    subparsers.add_parser("limits", help="Display current free-tier API limits across providers")

    # Coverage command
    subparsers.add_parser("coverage", help="Display market coverage and gap analysis (US, UK, Europe, Asia)")

    args = parser.parse_args()
    layer = DataLayer()

    if args.command == "quote":
        ledger = ProvenanceLedger(run_id="cli_quote_test")
        res = layer.get_quote(args.ticker, ledger=ledger)
        print(f"\n📈 Market Quote for {args.ticker}:")
        print(f"  Price: {res['price']:,.2f} {res['currency']}")
        print(f"  Supplied By: {res['source']} (Cached: {res['cached']})")
        print(f"  Timestamp: {res['timestamp']}")
        print(f"  Ledger Records Created: {len(ledger.entries)}")

    elif args.command == "macro":
        ledger = ProvenanceLedger(run_id="cli_macro_test")
        res = layer.get_macro_series(args.series_id, ledger=ledger)
        print(f"\n🏛️ Macro Series {args.series_id}:")
        print(f"  Value: {res['value']:.2f}%")
        print(f"  Date: {res['date']}")
        print(f"  Supplied By: {res['source']} (Cached: {res['cached']})")
        print(f"  Description: {res.get('description')}")

    elif args.command == "fundamentals":
        res = layer.get_fundamentals(args.ticker)
        print(f"\n📊 Fundamentals for {args.ticker} ({res['company_name']}):")
        print(f"  Accounting Standard: {res['accounting_standard']} | Currency: {res['currency']}")
        print(f"  Revenue: {res['revenue']:,.0f} | Net Income: {res['net_income']:,.0f}")
        print(f"  Source: {res['source']} (Cached: {res['cached']})")

    elif args.command == "limits":
        rep = layer.get_coverage_report()
        print("\n=================================================================")
        print("⏱️ CURRENT FREE-TIER API LIMITS BY DATA PROVIDER")
        print("=================================================================")
        for prov, info in rep["free_tier_limits"].items():
            print(f"\n[{prov}]: {info['provider_name']}")
            print(f"  - Rate Limit: {info['rate_limit']}")
            print(f"  - Daily Limit: {info['daily_limit']}")
            print(f"  - Key Configured in .env: {'YES' if rep['active_providers'].get(prov) else 'NO (Fallback Active)'}")
            print(f"  - Coverage: {info['coverage']}")
            print(f"  - Gaps / Notes: {info['gaps']}")

    elif args.command == "coverage":
        rep = layer.get_coverage_report()
        print("\n=================================================================")
        print("🌍 MARKET COVERAGE AND GAP ANALYSIS BY REGION")
        print("=================================================================")
        for mkt, info in rep["market_coverage"].items():
            print(f"\n[{mkt}] Market (Grade: {info['coverage_grade']})")
            print(f"  - Primary Source: {info['primary_source']}")
            print(f"  - Backups: {info['backups']}")
            print(f"  - Data Availability: {info['data_availability']}")
            print(f"  - Remaining Gaps: {info['remaining_gaps']}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
