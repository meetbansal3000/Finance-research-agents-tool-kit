"""
tools/r_bridge.py - Antigravity <-> RStudio / R Bridge
Enables bidirectional communication between Antigravity Python Agents and RStudio:
  1. Invokes R scripts and econometric routines via Rscript.exe (D:\\rstudio\\R-4.6.1)
  2. Runs Monte Carlo DCF simulations and econometric risk modeling using native R statistical libraries
  3. Records all R operations into ProvenanceLedger with source tag R_STUDIO_EXEC
"""

import os
import sys
import json
import shutil
import subprocess
from typing import Dict, Any, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from tools.ledger import ProvenanceLedger

DEFAULT_R_PATH = r"D:\rstudio\R-4.6.1\bin\Rscript.exe"
DEFAULT_RSTUDIO_EXE = r"D:\RStudio-IDE\rstudio.exe"


class RStudioBridge:
    def __init__(self, rscript_path: Optional[str] = None):
        self.rscript_path = self._locate_rscript(rscript_path)
        self.rstudio_exe = DEFAULT_RSTUDIO_EXE if os.path.exists(DEFAULT_RSTUDIO_EXE) else shutil.which("rstudio")

    def _locate_rscript(self, custom_path: Optional[str]) -> str:
        if custom_path and os.path.exists(custom_path):
            return custom_path
        if os.path.exists(DEFAULT_R_PATH):
            return DEFAULT_R_PATH
        found = shutil.which("Rscript")
        if found:
            return found
        return "Rscript"

    def is_available(self) -> bool:
        """Verify whether R executable is callable."""
        try:
            res = subprocess.run(
                [self.rscript_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return res.returncode == 0
        except Exception:
            return False

    def execute_expression(self, expr: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute an inline R expression and capture stdout/stderr."""
        try:
            res = subprocess.run(
                [self.rscript_path, "-e", expr],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=PROJECT_DIR
            )
            return {
                "success": (res.returncode == 0),
                "exit_code": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip()
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "error": str(e)
            }

    def run_monte_carlo_dcf(
        self,
        base_fcf: float,
        shares_outstanding: float,
        net_debt: float = 0.0,
        wacc_mean: float = 0.09,
        wacc_sd: float = 0.008,
        growth_mean: float = 0.08,
        growth_sd: float = 0.02,
        terminal_g: float = 0.025,
        n_sim: int = 1000,
        ledger: Optional[ProvenanceLedger] = None
    ) -> Dict[str, Any]:
        """
        Executes a vectorized Monte Carlo DCF simulation in R,
        computing empirical quantiles (5%, 25%, 50%, 75%, 95%) and Value-at-Risk (VaR).
        """
        r_cmd = (
            f"source('r_studio/agent_bridge.R'); "
            f"mc <- r_monte_carlo_dcf(base_fcf={base_fcf}, shares_outstanding={shares_outstanding}, "
            f"net_debt={net_debt}, wacc_mean={wacc_mean}, wacc_sd={wacc_sd}, "
            f"growth_mean={growth_mean}, growth_sd={growth_sd}, terminal_g={terminal_g}, n_sim={n_sim}); "
            f"cat(jsonlite::toJSON(list(mean=mc$mean_fair_value, sd=mc$sd_fair_value, median=mc$median_fair_value, "
            f"q05=unname(mc$quantiles['5%']), q25=unname(mc$quantiles['25%']), q50=unname(mc$quantiles['50%']), "
            f"q75=unname(mc$quantiles['75%']), q95=unname(mc$quantiles['95%']), iterations=mc$iterations), auto_unbox=TRUE))"
        )

        res = self.execute_expression(r_cmd, timeout=30)
        if not res["success"]:
            raise RuntimeError(f"R Monte Carlo simulation failed: {res.get('stderr') or res.get('error')}")

        # Parse JSON output from R
        lines = [line.strip() for line in res["stdout"].splitlines() if line.strip().startswith("{")]
        if not lines:
            raise ValueError(f"Could not parse JSON result from R script: {res['stdout']}")
        
        parsed = json.loads(lines[-1])

        ledger_id = None
        if ledger:
            ledger_id = ledger.record(
                tool="tools.r_bridge.run_monte_carlo_dcf",
                inputs={
                    "base_fcf": base_fcf,
                    "shares_outstanding": shares_outstanding,
                    "net_debt": net_debt,
                    "wacc_mean": wacc_mean,
                    "growth_mean": growth_mean,
                    "iterations": n_sim
                },
                output=parsed.get("median"),
                raw_value=parsed.get("median"),
                source=f"RStudio/R Statistical Engine ({self.rscript_path})",
                notes=f"Monte Carlo DCF (n={n_sim}): 5% VaR=${parsed.get('q05', 0):.2f}, Median=${parsed.get('median', 0):.2f}, 95% Upside=${parsed.get('q95', 0):.2f}",
                source_tag="R_STUDIO_ECONOMETRICS"
            )

        return {
            "mean_fair_value": parsed.get("mean"),
            "sd_fair_value": parsed.get("sd"),
            "median_fair_value": parsed.get("median"),
            "quantiles": {
                "5%": parsed.get("q05"),
                "25%": parsed.get("q25"),
                "50%": parsed.get("q50"),
                "75%": parsed.get("q75"),
                "95%": parsed.get("q95")
            },
            "iterations": parsed.get("iterations"),
            "ledger_id": ledger_id
        }

    def launch_rstudio(self) -> bool:
        """Launches RStudio IDE opened directly to finance-agents.Rproj."""
        if not self.rstudio_exe or not os.path.exists(self.rstudio_exe):
            return False
        rproj_file = os.path.join(PROJECT_DIR, "finance-agents.Rproj")
        subprocess.Popen([self.rstudio_exe, rproj_file])
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity RStudio Bridge")
    parser.add_argument("command", choices=["status", "monte-carlo", "launch"], help="Command to run")
    parser.add_argument("--base-fcf", type=float, default=100.0)
    parser.add_argument("--shares", type=float, default=10.0)
    parser.add_argument("--sims", type=int, default=1000)

    args = parser.parse_args()
    bridge = RStudioBridge()

    if args.command == "status":
        avail = bridge.is_available()
        print("=" * 60)
        print("📊 Antigravity <-> RStudio Bridge Status")
        print("=" * 60)
        print(f"Rscript Path : {bridge.rscript_path} (Available: {avail})")
        print(f"RStudio IDE  : {bridge.rstudio_exe} (Exists: {os.path.exists(bridge.rstudio_exe)})")
        if avail:
            res = bridge.execute_expression("cat(R.version.string)")
            print(f"R Version    : {res.get('stdout')}")
        print("=" * 60)

    elif args.command == "monte-carlo":
        print(f"🎲 Running R Monte Carlo DCF ({args.sims} iterations)...")
        res = bridge.run_monte_carlo_dcf(base_fcf=args.base_fcf, shares_outstanding=args.shares, n_sim=args.sims)
        print("Results:")
        print(f"  5% VaR       : ${res['quantiles']['5%']:.2f}")
        print(f"  25% Quartile : ${res['quantiles']['25%']:.2f}")
        print(f"  50% Median   : ${res['median_fair_value']:.2f}")
        print(f"  75% Quartile : ${res['quantiles']['75%']:.2f}")
        print(f"  95% Upside   : ${res['quantiles']['95%']:.2f}")

    elif args.command == "launch":
        print(f"🚀 Launching RStudio IDE at: {bridge.rstudio_exe}...")
        ok = bridge.launch_rstudio()
        if ok:
            print("  ✓ RStudio IDE opened successfully.")
        else:
            print("  ❌ Failed to launch RStudio IDE.")


if __name__ == "__main__":
    main()
