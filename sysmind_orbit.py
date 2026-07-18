"""Context builder. Rings + budget."""
import json
import re
from pathlib import Path
from typing import Dict, Any, List

from sysmind_common import ATLAS_FILE

QUERY_PATTERNS = {
    "packages": ["update", "upgrade", "outdated", "package", "apt"],
    "disk": ["disk", "space", "full", "storage", "cleanup", "clean"],
    "security": ["security", "port", "hack", "firewall", "intrusion", "attack"],
    "performance": ["slow", "lag", "performance", "cpu", "memory", "ram", "freeze"],
    "service": ["start", "stop", "restart", "service", "won't start", "failed"],
    "summary": ["summary", "status", "overview", "health"],
}


def classify_query(query: str) -> str:
    q = query.lower()
    for category, keywords in QUERY_PATTERNS.items():
        if any(kw in q for kw in keywords):
            return category
    return "general"


def build_context(query: str, atlas: Dict[str, Any], budget: int = 4000) -> str:
    category = classify_query(query)
    lines = ["# System Context Brief", f"Generated: {atlas.get('generated_at', 'unknown')}", f"Focus: {query}", ""]

    # Ring 0: Focus
    lines.append("## Ring 0 — Focus")
    if category == "packages":
        pkg = atlas.get("packages", {})
        lines.append(f"- Installed: {pkg.get('installed', '?')}")
        lines.append(f"- Upgradable: {pkg.get('upgradable', '?')}")
        lines.append(f"- Orphaned: {pkg.get('orphaned', '?')}")
    elif category == "disk":
        res = atlas.get("resources", {})
        lines.append(f"- Root disk: {res.get('disk_root_percent', '?')}% full")
        lines.append(f"- Available: {res.get('disk_root_avail', '?')}")
    elif category == "security":
        sec = atlas.get("security", {})
        lines.append(f"- Open ports: {sec.get('open_ports', [])}")
        lines.append(f"- Recent logins: {len(sec.get('recent_logins', []))} entries")
    elif category == "performance":
        res = atlas.get("resources", {})
        lines.append(f"- Load: {res.get('load', '?')}")
        lines.append(f"- Memory: {res.get('memory_percent', '?')}%")
    elif category == "service":
        svc = atlas.get("services", {})
        lines.append(f"- Running: {svc.get('running', '?')}")
        lines.append(f"- Failed: {svc.get('failed', '?')}")
        if svc.get("failed_services"):
            lines.append(f"- Failed services: {', '.join(svc['failed_services'][:5])}")
    else:
        lines.append("- General system query")
    lines.append("")

    # Ring 1: Direct deps (always include alerts)
    lines.append("## Ring 1 — Alerts & Direct Context")
    for alert in atlas.get("alerts", []):
        lines.append(f"- [{alert['level']}] {alert['message']}")
    lines.append("")

    # Ring 2: System skeleton
    if budget >= 4000:
        lines.append("## Ring 2 — System Context")
        sys_info = atlas.get("system", {})
        lines.append(f"- OS: {sys_info.get('os', '?')}")
        lines.append(f"- Kernel: {sys_info.get('kernel', '?')}")
        lines.append(f"- Uptime: {sys_info.get('uptime', '?')}")
        res = atlas.get("resources", {})
        lines.append(f"- Load: {res.get('load', '?')}, Memory: {res.get('memory_percent', '?')}%")
        lines.append("")

    # Ring 3: Parrot-specific
    if budget >= 8000:
        lines.append("## Ring 3 — Parrot Specific")
        parrot = atlas.get("parrot", {})
        lines.append(f"- Anonsurf: {'yes' if parrot.get('anonsurf_available') else 'no'}")
        lines.append(f"- Firejail: {'yes' if parrot.get('firejail_available') else 'no'}")
        lines.append("")

    lines.append(f"# User Query")
    lines.append(f"{query}")
    lines.append("")

    context = "\n".join(lines)
    return context


def main():
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "system status"
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
    with open(ATLAS_FILE) as f:
        atlas = json.load(f)
    ctx = build_context(query, atlas, budget)
    print(ctx)


if __name__ == "__main__":
    main()
