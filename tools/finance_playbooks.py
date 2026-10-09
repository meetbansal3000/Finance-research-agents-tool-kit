"""Read-only index for the OpenAccountant finance playbooks installed in this repo."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
SKILLS_DIR = PROJECT_DIR / ".agents" / "skills"
LOCK_PATH = PROJECT_DIR / "skills-lock.json"


def _frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Read the small name/description subset used by SKILL.md frontmatter."""
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", content, re.DOTALL)
    if not match:
        return {}, content

    metadata: dict[str, str] = {}
    description_lines: list[str] = []
    in_description = False
    for line in match.group(1).splitlines():
        if line.startswith("name:"):
            metadata["name"] = line.partition(":")[2].strip().strip("\"'")
            in_description = False
        elif line.startswith("description:"):
            value = line.partition(":")[2].strip().strip("\"'")
            if value and value != ">":
                description_lines.append(value)
            in_description = value == ">" or not value
        elif in_description:
            description_lines.append(line.strip().strip("\"'"))
    metadata["description"] = " ".join(part for part in description_lines if part).strip()
    return metadata, match.group(2)


def _section(body: str, heading: str) -> str:
    pattern = rf"(?ims)^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, body)
    return match.group(1).strip() if match else ""


def _bullet_items(section: str) -> list[str]:
    return [
        re.sub(r"\s+—\s+.*$", "", line.lstrip("-* ")).strip(" `")
        for line in section.splitlines()
        if line.lstrip().startswith(("- ", "* "))
    ]


def load_openaccountant_playbooks() -> list[dict[str, Any]]:
    """Load only skills pinned to OpenAccountant in the repository lockfile."""
    if not LOCK_PATH.is_file():
        return []

    try:
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    entries = lock.get("skills", {})
    playbooks: list[dict[str, Any]] = []
    for slug, record in sorted(entries.items()):
        if record.get("source") != "openaccountant/skills":
            continue
        path = SKILLS_DIR / slug / "SKILL.md"
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue

        metadata, body = _frontmatter(content)
        skill_path = str(record.get("skillPath", ""))
        category = skill_path.split("/", 1)[0].title() or "Finance"
        wilson_tools = _bullet_items(_section(body, "Wilson Tools Used"))
        pro_required = bool(re.search(r"(?i)(Wilson Pro|Plaid integration requires)", body))
        playbooks.append(
            {
                "slug": slug,
                "name": metadata.get("name") or slug.replace("-", " ").title(),
                "description": metadata.get("description") or "Open the playbook to review its workflow.",
                "category": category,
                "body": body.strip(),
                "wilson_tools": wilson_tools,
                "pro_required": pro_required,
                "source_path": skill_path,
                "manual_workflow": _section(body, "Without Wilson"),
            }
        )
    return playbooks

