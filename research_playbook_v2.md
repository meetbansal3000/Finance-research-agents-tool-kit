# Research Playbook v2 (global, multi-style)

## Standing rules (every task)

1. Every number needs a source: filing URL and form type, or the data tool plus the date pulled. No source, no number.
2. State the accounting standard (US GAAP, IFRS, J-GAAP, Ind AS, HKFRS, CAS), the currency, and the fiscal year-end for every company. Never compare across companies without noting differences.
3. Show the arithmetic for any ratio or growth rate. Say which period each figure covers.
4. Prefer the company's own filings over aggregator data. If they disagree, report both.
5. Label price data with its timestamp. Note if it may be delayed.
6. Separate facts from interpretation. Mark interpretation clearly.
7. Say what you could not find or verify. Do not fill gaps with guesses.
8. Research only, no buy/sell calls. Give the bull case, the bear case, and what would change the picture.
9. Save each output to `/reports/TICKER_task_YYYY-MM-DD.md`.
10. Stay inside this project folder. Ask before installing anything new.
11. Never do arithmetic yourself, always call the calculation toolkit in `/tools/calc/`.
12. Check the local knowledge base (`/tools/knowledge.py`) before searching the web. Always search local primary filings, transcripts, and notes before making external calls.

---

## Market module: where to get data

Tickers use Yahoo-style suffixes in OpenBB/yfinance. Confirm the listing exchange before pulling anything.

| Market | Suffix | Primary filings source | Notes |
|---|---|---|---|
| US | none | SEC EDGAR (EdgarTools, sec-edgar-mcp) | Best coverage. 10-K, 10-Q, 8-K, Form 4, 13F. |
| UK | .L | RNS announcements on the LSE site; Companies House for private filings | Half-year reporting, not quarterly. IFRS. |
| Germany | .DE | Company IR site (ESEF annual report); Bundesanzeiger | Half-year or quarterly depending on listing. IFRS. |
| France | .PA | AMF / company IR (ESEF) | IFRS. |
| Netherlands | .AS | AFM / company IR | IFRS. |
| Switzerland | .SW | SIX Exchange Regulation / company IR | IFRS or Swiss GAAP FER. |
| Japan | .T | EDINET (annual securities report), TDnet (timely disclosures) | J-GAAP, IFRS, or US GAAP depending on company. March year-end is common. |
| Hong Kong | .HK | HKEXnews | HKFRS/IFRS. Check for connected-transaction disclosures. |
| China A-shares | .SS / .SZ | SSE / SZSE announcements, CNINFO | CAS. Data is patchy in English. Flag translation risk. |
| India | .NS / .BO | NSE and BSE corporate filings | Ind AS. March year-end. Check promoter pledging and shareholding patterns. |
| Korea | .KS | DART | K-IFRS. |
| Singapore | .SI | SGX announcements | SFRS(I), IFRS-aligned. |

Rule for any non-US company: pull the original filing (use the web agent/scraper if no MCP covers it), then cross-check key figures against the data tool. If only the data tool is available, say so and lower confidence.

Cross-border adjustments to check every time:
- IFRS 16 vs US GAAP lease treatment affects EBITDA and net debt. Compare on a consistent basis.
- IFRS allows capitalising development costs, US GAAP mostly does not. Matters for tech and pharma.
- Different fiscal year-ends. Calendarise before comparing.
- Report currency vs. listing currency vs. where revenue is earned. Note FX exposure.
- Dual listings and ADRs: say which line you are valuing.
- Withholding tax on dividends differs by country.

---

## Workflow 1: Single-stock deep dive (any market)

1. Identify the listing, ticker, exchange, currency, accounting standard, fiscal year-end.
2. Business: what it sells, how it earns money, segments, geographic mix. From the latest annual report.
3. Financials: 5 years of revenue, gross margin, operating margin, net income, free cash flow, net debt. Table form.
4. Quality checks: revenue growth vs. receivables growth, cash conversion (CFO / net income), share count trend, restatements, auditor changes, related-party transactions.
5. Risks: what changed in risk disclosures versus the prior year.
6. Ownership and insiders: Form 4 (US), director dealings (UK/EU RNS and MAR notifications), promoter holding and pledging (India), major shareholder filings (HK, Japan).
7. Valuation: P/E, EV/EBITDA, P/FCF vs. own 5-year range and 3 named peers, on a consistent accounting basis.
8. Output: one-page summary, then detail. End with bull case, bear case, 3 things to monitor.

## Workflow 2: Value

1. Screen: low P/E, P/B, EV/EBIT, or FCF yield vs. own history and sector.
2. Check why it is cheap: cyclical trough, structural decline, accounting issue, governance, or neglect.
3. Balance sheet: net debt/EBITDA, interest cover, debt maturity, pension deficits, off-balance-sheet items.
4. Normalised earnings: strip one-offs, use a through-the-cycle margin, state assumptions.
5. Value trap tests: falling revenue, shrinking returns on capital, dividend not covered by free cash flow, heavy buybacks funded by debt.
6. Output: a rough fair value range with the assumptions that drive it, and what would prove the thesis wrong.

## Workflow 3: Growth and quality compounders

1. Revenue growth rate and its drivers: volume, price, acquisitions, FX. Separate organic from reported.
2. Unit economics where available: gross margin trend, customer retention, net revenue retention, backlog.
3. Returns on invested capital over 5+ years. Reinvestment rate.
4. Operating leverage: how margins move as revenue grows.
5. Dilution: stock-based comp as % of revenue and net share count change.
6. Valuation vs. growth: EV/sales, PEG, and what growth is already priced in (reverse DCF).
7. Risks: competition, customer concentration, regulation, key-person dependence.

## Workflow 4: Event-driven

Pick the event type, then run its checklist.

**M&A target or acquirer:** deal terms, premium to undisturbed price, financing, conditions, regulatory approvals and timeline, break fee, shareholder vote threshold, comparable deals.
**Merger arbitrage:** spread, implied probability of completion, downside price if the deal fails, time to close, annualised return.
**Spin-offs:** reason, parent vs. spinco financials, debt allocation, index inclusion or exclusion effects, forced-selling risk.
**Activism:** stake size, stated demands, track record of the activist, board response, voting dynamics.
**Earnings:** see Workflow 5.
**Special situations:** restructurings, tender offers, rights issues, delistings, index changes, litigation outcomes. Always find the primary document (prospectus, offer document, court filing).

For every event: date of each catalyst, what the market currently implies, and what happens in each outcome.

## Workflow 5: Earnings prep

1. Last 4 quarters (or halves): revenue, EPS, margins vs. guidance. Include consensus if a source exists. If not, say so.
2. Last call: guidance changes, tone shifts, repeated themes, promises not yet delivered.
3. Key metrics to watch and the level that would count as a surprise either way.
4. Filings and news since the last report.

## Workflow 6: Income and dividends

1. Dividend history, payout ratio on earnings and free cash flow, growth rate.
2. Cover and sustainability: debt levels, capex needs, cyclicality.
3. Buybacks vs. dividends. Withholding tax impact for a UK-based holder by country.
4. Red flags: yield well above sector, payout over 100% of FCF, recent dividend cut by peers.

## Workflow 7: Macro and thematic

1. Define the theme or macro view (rates, inflation, a commodity, AI capex, energy transition).
2. Pull the relevant series: central bank rates, CPI, yield curves, PMI, commodity prices (FRED, ECB, BoE, and other sources available through OpenBB).
3. Map to sectors and listed names. Show which are direct beneficiaries and which are second-order.
4. State what data would confirm or break the view, with dates for upcoming releases.

## Workflow 8: Red flags and short-side check

1. Accounting: aggressive revenue recognition, rising days sales outstanding, capitalised costs, frequent non-GAAP adjustments, auditor resignations.
2. Governance: related-party deals, promoter pledging, dual-class control, board turnover.
3. Financial stress: covenants, refinancing wall, going-concern language.
4. Market signals: unusual insider selling, short interest where available.
5. Output: list of concerns ranked by severity, each with the exact filing reference.

## Workflow 9: Screen

Input: criteria and market. Build the universe, apply filters, show how many names pass each one. For the top 10, give a one-line reason it is interesting and one red flag. State data source limits.

## Workflow 10: Weekly watchlist briefing

Input: `watchlist.txt` with ticker, exchange suffix, and one-line thesis per row.
1. Price moves: 1 week, 1 month, YTD, in local currency.
2. New filings and announcements this week, across the relevant exchanges.
3. Material news per name, with links.
4. Macro calendar for the next week across your markets.
5. Flag anything that contradicts a thesis in the watchlist.

## Workflow 11: Compare two companies

Side by side: growth, margins, returns on capital, balance sheet, valuation, risks. Adjust for accounting standard, year-end, and currency. Finish with where each looks stronger and what the market seems to be pricing in.
