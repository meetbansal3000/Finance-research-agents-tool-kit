"""
tools/codex_bridge.py - Antigravity <-> OpenAI Codex CLI Bridge
Enables bidirectional communication between Google Antigravity and OpenAI Codex CLI:
  1. Non-interactive prompt execution via 'codex exec'
  2. Automated code review via 'codex exec review'
  3. Structured output capture with session ID and token accounting
  4. Integration with ProvenanceLedger for cross-agent audit trails
"""

import os
import sys
import json
import subprocess
import datetime
import shutil
from typing import Dict, Any, Optional, List

# Ensure project root is in sys.path
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from tools.ledger import ProvenanceLedger


class CodexBridge:
    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = working_dir or PROJECT_DIR
        self.codex_cmd = self._find_codex_binary()

    def _find_codex_binary(self) -> str:
        """Finds the Codex CLI executable portably on the host system."""
        found = shutil.which("codex")
        if found:
            return found
        # Fallback to antigravity-ide bin on Windows
        ide_path = os.path.expanduser(r"~\.gemini\antigravity-ide\bin\codex.cmd")
        if os.path.exists(ide_path):
            return ide_path
        return "codex"

    def execute(
        self,
        prompt: str,
        sandbox: str = "read-only",
        model: Optional[str] = None,
        timeout: int = 120,
        ledger: Optional[ProvenanceLedger] = None
    ) -> Dict[str, Any]:
        """
        Executes a prompt non-interactively using 'codex exec'.
        Pipes DEVNULL to stdin to prevent interactive prompts from blocking.
        """
        cmd = [self.codex_cmd, "-C", self.working_dir, "exec", "--sandbox", sandbox]
        if model:
            cmd.extend(["-m", model])
        cmd.append(prompt)

        full_cmd = list(cmd)
        if sys.platform == "win32" and (str(self.codex_cmd).lower().endswith(".cmd") or str(self.codex_cmd).lower().endswith(".bat")):
            full_cmd = ["cmd.exe", "/c"] + full_cmd

        start_time = datetime.datetime.now()
        try:
            res = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=timeout,
                shell=False
            )
            elapsed = (datetime.datetime.now() - start_time).total_seconds()
            
            output = res.stdout.strip()
            error = res.stderr.strip()
            success = (res.returncode == 0)

            parsed = self._parse_codex_output(output)

            # Record in ledger if provided
            ledger_id = None
            if ledger:
                ledger_id = ledger.record(
                    tool="codex_bridge.execute",
                    inputs={"prompt": prompt[:100], "sandbox": sandbox},
                    output=parsed.get("response", "")[:200],
                    source=f"OpenAI Codex CLI ({parsed.get('model', 'default')})",
                    notes=f"Codex Session: {parsed.get('session_id', 'N/A')}, Tokens: {parsed.get('tokens_used', 'N/A')}",
                    source_tag="CODEX_EXEC"
                )

            return {
                "success": success,
                "exit_code": res.returncode,
                "raw_output": output,
                "error": error if not success else None,
                "response": parsed.get("response", output),
                "model": parsed.get("model"),
                "session_id": parsed.get("session_id"),
                "tokens_used": parsed.get("tokens_used"),
                "elapsed_seconds": round(elapsed, 2),
                "ledger_id": ledger_id
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": -1,
                "error": f"Codex execution timed out after {timeout} seconds",
                "response": "",
                "elapsed_seconds": timeout
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "error": str(e),
                "response": "",
                "elapsed_seconds": 0.0
            }

    def review_codebase(self, target: str = "--uncommitted", timeout: int = 180) -> Dict[str, Any]:
        """Runs non-interactive code review across the repository."""
        cmd = [self.codex_cmd, "-C", self.working_dir, "exec", "review", target]
        full_cmd = list(cmd)
        if sys.platform == "win32" and (str(self.codex_cmd).lower().endswith(".cmd") or str(self.codex_cmd).lower().endswith(".bat")):
            full_cmd = ["cmd.exe", "/c"] + full_cmd
        try:
            res = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=timeout,
                shell=False
            )
            return {
                "success": (res.returncode == 0),
                "exit_code": res.returncode,
                "output": res.stdout.strip(),
                "error": res.stderr.strip() if res.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_codex_output(self, text: str) -> Dict[str, Any]:
        """Extracts metadata (session id, model, tokens used) and response from codex output."""
        metadata = {}
        lines = text.splitlines()
        response_lines = []
        is_response = False

        for line in lines:
            if line.startswith("model:"):
                metadata["model"] = line.split(":", 1)[1].strip()
            elif line.startswith("session id:"):
                metadata["session_id"] = line.split(":", 1)[1].strip()
            elif line.startswith("tokens used"):
                pass
            elif line.startswith("codex"):
                is_response = True
                continue
            elif is_response:
                if line.startswith("tokens used"):
                    is_response = False
                else:
                    response_lines.append(line)

        metadata["response"] = "\n".join(response_lines).strip() or text
        return metadata


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity Codex CLI Bridge")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Exec command
    e_p = subparsers.add_parser("exec", help="Execute prompt non-interactively via Codex")
    e_p.add_argument("prompt", type=str, help="Instruction or query for Codex")
    e_p.add_argument("--sandbox", type=str, default="read-only", choices=["read-only", "workspace-write", "danger-full-access"])
    e_p.add_argument("--model", type=str, default=None)

    # Review command
    subparsers.add_parser("review", help="Run automated Codex code review")

    args = parser.parse_args()
    bridge = CodexBridge()

    if args.command == "exec":
        print(f"🤖 Executing via Codex CLI (Sandbox: {args.sandbox})...\n")
        res = bridge.execute(args.prompt, sandbox=args.sandbox, model=args.model)
        if res["success"]:
            print("=" * 60)
            print(f"Session: {res.get('session_id')} | Model: {res.get('model')} | Elapsed: {res.get('elapsed_seconds')}s")
            print("=" * 60)
            print(res["response"])
        else:
            print(f"❌ Execution failed: {res.get('error')}")

    elif args.command == "review":
        print("🔍 Running Codex Code Review across repository...\n")
        res = bridge.review_codebase()
        if res["success"]:
            print(res["output"])
        else:
            print(f"❌ Review failed: {res.get('error')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
