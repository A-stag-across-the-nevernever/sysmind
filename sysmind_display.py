"""Dual-display detection and dashboard rendering."""
import subprocess
import json
from typing import Dict, List, Optional

from sysmind_common import run_cmd


def get_displays() -> List[Dict[str, str]]:
    """Detect displays via xrandr or wlr-randr."""
    displays = []
    # Try xrandr first (X11)
    try:
        r = run_cmd(["xrandr", "--listmonitors"], check=False)
        if r.returncode == 0:
            for line in r.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    displays.append({
                        "name": parts[-1].strip("+*"),
                        "geometry": parts[-2] if "/" in parts[-2] else "unknown",
                        "primary": "+" in line,
                    })
    except Exception:
        pass
    # Fallback: try xrandr --query for connected displays
    if not displays:
        try:
            r = run_cmd(["xrandr", "--query"], check=False)
            for line in r.stdout.splitlines():
                if " connected " in line:
                    parts = line.split()
                    name = parts[0]
                    primary = "primary" in line
                    displays.append({"name": name, "geometry": "unknown", "primary": primary})
        except Exception:
            pass
    return displays


def get_secondary_display() -> Optional[Dict[str, str]]:
    displays = get_displays()
    if len(displays) < 2:
        return None
    # Return non-primary display, or second display
    for d in displays:
        if not d.get("primary"):
            return d
    return displays[1] if len(displays) > 1 else None


def render_dashboard(atlas: dict) -> str:
    alerts = atlas.get("alerts", [])
    res = atlas.get("resources", {})
    if any(a["level"] == "crit" for a in alerts):
        status = "🔴"
    elif any(a["level"] == "warn" for a in alerts):
        status = "🟡"
    else:
        status = "🟢"

    lines = [
        f"{status} Parrot System Mind",
        f"Last scan: recent",
        "",
        f"Disk: {res.get('disk_root_percent', '?')}%",
        f"Mem:  {res.get('memory_percent', '?')}%",
        f"Load: {res.get('load', '?')}",
        "",
    ]
    for a in alerts[:5]:
        icon = "✅" if a["level"] == "info" else "⚠️"
        lines.append(f"{icon} {a['message']}")
    lines.append("")
    lines.append("[Menu] [Ask] [Undo]")
    return "\n".join(lines)


def open_on_display(cmd: List[str], display_name: str) -> None:
    """Open a terminal on a specific display. Simplified — opens in current terminal."""
    subprocess.Popen(cmd)


def main():
    displays = get_displays()
    print(f"Displays found: {len(displays)}")
    for d in displays:
        print(f"  {d['name']} (primary={d.get('primary', False)})")
    sec = get_secondary_display()
    if sec:
        print(f"Secondary: {sec['name']}")
    else:
        print("No secondary display detected.")


if __name__ == "__main__":
    main()
