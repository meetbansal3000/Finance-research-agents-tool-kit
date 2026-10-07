# Independent Code & Use-Case Audit Report (OpenAI Codex)
**Generated:** 2026-10-07 14:45:25  
**Auditor Engine:** OpenAI Codex CLI (Model: None)  
**Session ID:** `None`  
**Provenance Ledger ID:** `[LEDGER_0002]`  

---

## 1. Executive Summary

This audit reviews the repository’s DCF calculations, data layer, filing extraction, multi-agent workflow, and overall readiness. It is based on source inspection of the implementation, tests, and existing reports. I did not run tests or live data checks, so findings about runtime behavior are code-based rather than execution-verified.

The project has a useful foundation: deterministic valuation functions, period-aware SEC extraction paths, source tags, and a report verification workflow. The main risks are gaps between those safeguards and their claims. In particular, the DCF accepts some invalid inputs, the rate limiter and quota guard are not safe across concurrent processes, non-US filing support is uneven, and HMAC integrity depends on a hard-coded fallback secret when no environment key is configured.

**Overall score: 6.5/10 — promising research tooling, but not yet institutional-grade without addressing the controls and coverage gaps below.**

## 2. DCF Audit

**Assessment: Core formulas are recognizable and deterministic; input validation and output labeling need work.**

`dcf()` projects each year’s FCF, discounts explicit cash flows, calculates a Gordon growth terminal value, subtracts net debt, and divides by shares. The analytical test independently calculates a five-year example and checks the result. `reverse_dcf()` uses bisection to solve for constant growth and has a corresponding recovery test.

Key findings:

- **Empty projections can fail unclearly.** `dcf()` indexes `projected_fcf[-1]`, so an empty `growth_rates` list raises `IndexError`. There is no explicit validation that at least one projection year is supplied.
- **Inputs are only partly validated.** The function checks `discount_rate > terminal_growth_rate` and positive shares, but does not reject non-finite values or validate the growth-rate entries. Negative FCF may be valid for some companies, but its use in a perpetual growth model should be surfaced explicitly.
- **Reverse DCF can return a boundary without reporting that no root was found.** If the target price lies outside the searched range, the solver returns a bound (up to 2000% growth or down to -99%) as the implied growth rate. That can look like a solved value unless callers inspect the result.
- **Output formatting assumes dollars.** The formatted DCF string uses `$` regardless of the issuer’s currency. The calculation itself is currency-neutral, but the label can be wrong for non-USD reports.
- **Model scope should be made explicit.** This is a constant terminal-growth model, and `reverse_dcf()` assumes a constant growth rate over the projection period. The API does not model dilution, changing share count, or separate cash flows for non-controlling interests.

**Recommendation:** Validate projection length and finite inputs; add a solver status indicating convergence or boundary saturation; and pass currency into formatting. Keep the assumptions visible in reports, including base FCF period, WACC, terminal growth, and share count.

## 3. DataLayer Audit

**Assessment: Useful fallback and caching structure; concurrency and data freshness controls are insufficient.**

The data layer provides quote fallback across cache, yfinance, Finnhub, FMP, and Alpha Vantage; has separate quote and financial TTLs; and records provider information in the ledger. It also offers batch quote retrieval and macro-series support.

Key findings:

- **The “token bucket” is a per-process minimum-delay limiter.** It tracks only `last_call` in memory. Separate processes do not coordinate, and concurrent threads can pass the same check before either updates the timestamp.
- **Alpha Vantage quota tracking is vulnerable to races.** The daily JSON file is read and rewritten without locking or an atomic update. Concurrent callers may exceed the intended daily cap. The counter is incremented before the request outcome is known, which is conservative but can consume quota on failed calls.
- **Batch retrieval is sequential.** `get_quotes_batch()` checks cache, then calls `get_quote()` once per missing ticker; the code does not show a provider-level batch request or a shared request for yfinance data.
- **Fallback values are not interchangeable.** Quote fallback is reasonable when provider and timestamp stay attached. For fundamentals, the README correctly warns that secondary sources do not replace audited filings; callers must preserve this distinction in downstream calculations and reports.
- **Cache behavior needs stronger validation.** Cache read/write errors are silently ignored. This avoids crashes but can hide persistent failures. Cached responses retain their source, but users need the quote timestamp and cache age to judge freshness.

**Recommendation:** Use a shared, lock-protected rate and quota store if multiple workers can run concurrently; expose cache age and source timestamp in outputs; and keep audited financials separate from provider summary data. Treat provider limit descriptions as configuration or documentation requiring periodic verification, not as enforced guarantees.

## 4. Filings Audit

**Assessment: Strong period matching in the 20-F path; filing coverage is incomplete and some metadata is not carried through consistently.**

The filing module includes dedicated paths for specific US filings, SEC company facts, Form 20-F IFRS facts, and ESEF iXBRL parsing. In the 20-F extractor, revenue anchors the period, and other facts are filtered to the same form, period end, accession, and currency before ledger registration. That is a meaningful period-integrity control.

Key findings:

- **The 20-F extractor depends on SEC company-facts taxonomy coverage.** It returns an error if `ifrs-full` is absent and searches a limited set of candidate tags. A missing tag does not establish that a metric is absent from the filing; it may be disclosed under another taxonomy concept or only in the filing document.
- **Instant facts are matched by accession and end date, but not fiscal year.** That can be acceptable for balance-sheet facts, yet the selection should still be checked against the filing’s reporting date and unit conventions.
- **The TCS path is company-specific.** It supports a particular audited results source, not a general exchange-report extraction framework.
- **ESEF parsing is document-dependent.** It extracts tagged iXBRL facts, but source inspection alone does not establish broad coverage of namespaces, contexts, units, duplicate facts, or company-specific extensions.
- **Some analyst paths use generic market-provider financials.** Those entries are tagged as yfinance/provider data, but they do not meet the repository’s stated standard for audited financial figures. Reports need to clearly distinguish these from primary filing-derived values.
- **Not every ledger record is equally complete.** The 20-F registration includes fiscal year, period end, and accession in source text, while some other paths rely on inputs or source strings and may omit explicit accession or period fields.

**Recommendation:** Define an explicit source-eligibility rule for each reported metric. For each filing-derived value, retain form, accession, period end, fiscal year, unit, currency, and a filing or fact URL as structured fields. Report missing or unsupported facts as unavailable rather than substituting provider data.

## 5. Multi-Agent and Provenance Audit

**Assessment: The workflow has useful separation of roles, but the verification boundary and ledger security need clearer guarantees.**

The architecture coordinates analyst extraction, verifier checks, an optional correction round, and skeptic review. A note extractor handles textual disclosures. The verifier parses report claims, checks ledger references and precision, and can re-fetch selected sources.

Key findings:

- **“Independent” verification is limited by the implemented refetch routes.** The verifier’s source re-fetch is keyed to specific tool names and source types. It should not be treated as independent confirmation for every ledger entry unless that entry’s source type is explicitly covered.
- **A correction round is not equivalent to a second independent analysis.** The analyst edits claims based on verifier findings; the verifier must then re-audit the corrected report, and unresolved or unsupported items must remain visible.
- **Ledger IDs are deterministic within a run, not globally unique.** IDs restart at `LEDGER_0001` for each ledger instance. They need run or sidecar context when cited outside the report bundle.
- **The ledger’s fallback HMAC key is hard-coded.** If `LEDGER_HMAC_KEY` is not set, signatures use a repository-known default. That can detect accidental edits but does not provide meaningful protection against a party who knows the code and key.
- **HMAC does not establish source truth.** It protects the signed ledger fields from later alteration under a secret key; it does not prove that the source was primary, that extraction was correct, or that the original entry was truthful.
- **Text extraction can miss or misclassify disclosures.** The note extractor only treats an explicit concentration identification as a percentage result. “No concentration disclosed” should not be interpreted as zero concentration or a passed risk check.

**Recommendation:** Require a secret HMAC key in production and fail closed if absent. Include run ID in citation resolution, record structured source metadata, and label each verifier result by check performed: ledger consistency, refetch confirmed, or unverifiable. Keep unavailable disclosure checks distinct from passing checks.

## 6. Score and Priorities

| Area | Score | Main reason |
|---|---:|---|
| DCF | 7/10 | Core calculations and happy-path analytical tests exist; boundary handling and labeling need improvement. |
| DataLayer | 6/10 | Good fallback structure; concurrency, quota persistence, and freshness visibility are weak. |
| Filings | 6.5/10 | Strong 20-F period/accession matching; coverage and structured provenance vary by path. |
| Multi-Agent | 6.5/10 | Clear role separation and audit workflow; verification coverage and key management limit assurance. |
| **Overall** | **6.5/10** | Useful research prototype with real controls, but the current safeguards do not support the strongest “institutional-grade” claims. |

**Recommended order of work:**

1. Require a configured HMAC secret and make its absence an explicit configuration failure.
2. Fix DCF empty-input and reverse-solver boundary reporting; label currency correctly.
3. Make rate limiting and daily quota updates safe across concurrent processes.
4. Standardize filing provenance fields and make source eligibility explicit in reports.
5. Show verifier coverage and unavailable checks clearly in every final dossier.
