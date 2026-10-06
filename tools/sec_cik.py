"""
tools/sec_cik.py - Universal SEC EDGAR CIK Resolver and Company Directory
Provides dynamic O(1) resolution from US stock tickers to official 10-digit SEC CIKs
and company entity names for over 10,000 US public companies.
Caches sec_company_tickers.json locally to ensure zero rate limit issues and instant offline lookups.
"""

import os
import json
import urllib.request
import time
from typing import Dict, Any, Optional, Tuple

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "library", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "sec_company_tickers.json")

# Fallback dictionary for top US tickers in case network is completely disconnected
STATIC_FALLBACK = {
    "AAPL": ("0000320193", "Apple Inc."),
    "MSFT": ("0000789019", "Microsoft Corporation"),
    "NVDA": ("0001045810", "NVIDIA Corporation"),
    "GOOGL": ("0001652044", "Alphabet Inc."),
    "GOOG": ("0001652044", "Alphabet Inc."),
    "AMZN": ("0001018724", "Amazon.com, Inc."),
    "META": ("0001326801", "Meta Platforms, Inc."),
    "TSLA": ("0001318605", "Tesla, Inc."),
    "BRK.B": ("0001067983", "Berkshire Hathaway Inc."),
    "BRK.A": ("0001067983", "Berkshire Hathaway Inc."),
    "JPM": ("0000019617", "JPMorgan Chase & Co."),
    "JNJ": ("0000200406", "Johnson & Johnson"),
    "V": ("0001403161", "Visa Inc."),
    "UNH": ("0000731766", "UnitedHealth Group Inc"),
    "WMT": ("0000104169", "Walmart Inc."),
    "PG": ("0000080424", "Procter & Gamble Co"),
    "MA": ("0001141391", "Mastercard Inc"),
    "HD": ("0000354950", "Home Depot, Inc."),
    "CVX": ("0000093410", "Chevron Corporation"),
    "MRK": ("0000310158", "Merck & Co., Inc."),
    "ABBV": ("0001551152", "AbbVie Inc."),
    "COST": ("0000909832", "Costco Wholesale Corp"),
    "KO": ("0000021344", "Coca-Cola Co"),
    "PEP": ("0000077476", "PepsiCo, Inc."),
    "AVGO": ("0001730168", "Broadcom Inc."),
    "ORCL": ("0001341439", "Oracle Corporation"),
    "ADBE": ("0000796343", "Adobe Inc."),
    "CSCO": ("0000858877", "Cisco Systems, Inc."),
    "CRM": ("0001108524", "Salesforce, Inc."),
    "AMD": ("0000002488", "Advanced Micro Devices, Inc."),
    "INTC": ("0000050863", "Intel Corporation"),
    "QCOM": ("0000804328", "QUALCOMM Incorporated"),
    "TXN": ("0000097476", "Texas Instruments Inc"),
    "NFLX": ("0001065280", "Netflix, Inc."),
    "DIS": ("0001744489", "Walt Disney Co"),
}

class SecCikResolver:
    _instance: Optional['SecCikResolver'] = None
    _ticker_to_cik: Dict[str, str] = {}
    _ticker_to_name: Dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SecCikResolver, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        loaded = self._load_from_cache()
        if not loaded:
            self._fetch_and_cache()
            if not self._ticker_to_cik:
                # Apply static fallback if both cache and download fail
                for t, (cik, name) in STATIC_FALLBACK.items():
                    self._ticker_to_cik[t] = cik
                    self._ticker_to_name[t] = name

    def _load_from_cache(self) -> bool:
        if not os.path.exists(CACHE_FILE):
            return False
        try:
            # Check cache age (valid for 14 days)
            age_days = (time.time() - os.path.getmtime(CACHE_FILE)) / 86400.0
            if age_days > 14:
                return False

            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._populate_maps(data)
            return len(self._ticker_to_cik) > 0
        except Exception:
            return False

    def _fetch_and_cache(self) -> bool:
        url = "https://www.sec.gov/files/company_tickers.json"
        ua = os.getenv("SEC_EDGAR_USER_AGENT", "ResearchAnalyst research@example.com")
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self._populate_maps(data)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return True
        except Exception:
            # If fetch fails, try to load existing cache regardless of age
            if os.path.exists(CACHE_FILE):
                try:
                    with open(CACHE_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._populate_maps(data)
                    return True
                except Exception:
                    pass
            return False

    def _populate_maps(self, raw_data: Dict[str, Any]):
        self._ticker_to_cik.clear()
        self._ticker_to_name.clear()
        for row in raw_data.values():
            sym = str(row.get("ticker", "")).upper().strip()
            cik_num = row.get("cik_str")
            title = row.get("title", "")
            if sym and cik_num:
                padded_cik = str(cik_num).zfill(10)
                self._ticker_to_cik[sym] = padded_cik
                self._ticker_to_name[sym] = title

    def get_cik(self, ticker: str) -> Optional[str]:
        """Return 10-digit zero-padded CIK string for ticker."""
        clean = ticker.upper().strip()
        if clean in self._ticker_to_cik:
            return self._ticker_to_cik[clean]
        # Check static fallback
        if clean in STATIC_FALLBACK:
            return STATIC_FALLBACK[clean][0]
        return None

    def get_company_title(self, ticker: str) -> Optional[str]:
        """Return official company title for ticker."""
        clean = ticker.upper().strip()
        if clean in self._ticker_to_name:
            return self._ticker_to_name[clean]
        if clean in STATIC_FALLBACK:
            return STATIC_FALLBACK[clean][1]
        return None

    def is_us_listed(self, ticker: str) -> bool:
        """Return True if ticker is an SEC registered US company."""
        return self.get_cik(ticker) is not None

    def total_count(self) -> int:
        return len(self._ticker_to_cik)

# Global helper functions
def resolve_cik(ticker: str) -> Optional[str]:
    return SecCikResolver().get_cik(ticker)

def resolve_company_name(ticker: str) -> Optional[str]:
    return SecCikResolver().get_company_title(ticker)

def is_us_company(ticker: str) -> bool:
    return SecCikResolver().is_us_listed(ticker)
