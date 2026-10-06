"""
Run 11 hold-out sentences before code modifications to capture raw output.
"""
import sys
sys.path.insert(0, ".")
import json
from tools.ledger import ProvenanceLedger
from agents.verifier import ReportVerifier

ledger = ProvenanceLedger(run_id="raw_eval_11")
l1 = ledger.record(tool="edgar.get_facts", ticker="AAPL", inputs={"ticker": "AAPL"}, output=416161000000.0, raw_value=416161000000.0, source="SEC 10-K", period="FY2025")
l2 = ledger.record(tool="tools.calc.margin", ticker="AAPL", inputs={"ticker": "AAPL"}, output=31.97, raw_value=31.97, source="SEC 10-K", period="FY2025")
l3 = ledger.record(tool="edgar.get_facts", ticker="AAPL", inputs={"ticker": "AAPL"}, output=112010000000.0, raw_value=112010000000.0, source="SEC 10-K", period="FY2025")

sentences = [
    f"Revenue was $416,161M [{l1}].",
    f"Net income of $112.0B [{l3}] missed consensus by 3%.",
    f"Operating margin was 31.97% [{l2}] in the December quarter.",
    "[ANALYSIS] Apple holds roughly 70% of premium smartphone profits.",
    f"Revenue was £416.2B [{l1}].",
    "## Apple grew revenue 40% in FY2025",
    f"- Revenue is up over 50% in two years [{l1}].",
    f"Net income was $112,010M [{l3}] <!-- and R&D was $500B -->",
    f"Revenue and net income were $416,161M and $112,010M respectively [{l1}][{l3}].",
    f"Net income [{l3}] was $112.0B, while R&D [LEDGER_0009] was $34B.",
    "[UNVERIFIED: model memory] Apple's top customer is 22% of revenue."
]

with open("test_11_raw.md", "w", encoding="utf-8") as f:
    f.write("\n".join(sentences))
ledger.save_sidecar("test_11_raw.provenance.json")

verifier = ReportVerifier("test_11_raw.md")
audit = verifier.audit()

print("=== RAW CONFIRMED ===")
for c in audit["confirmed"]:
    print(c)

print("\n=== RAW WRONG ===")
for w in audit["wrong"]:
    print(w)

print("\n=== RAW UNVERIFIABLE ===")
for u in audit["unverifiable"]:
    print(u)
