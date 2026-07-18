"""Choice-driven setup wizard for sysmind."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
BIN_DIR = Path.home() / ".local" / "bin"
CONFIG_DIR = Path.home() / ".config" / "sysmind"
DATA_DIR = Path.home() / ".local" / "share" / "sysmind"
LIB_DIR = DATA_DIR / "lib"

# Curated pairs: a language-strong conscious slot beside an ops-strong
# unconscious one. Same table sysmind_doctor recommends from.
MODEL_PAIRS = {
    "4gb":  ("qwen3:1.7b", "qwen2.5-coder:1.5b"),
    "8gb":  ("qwen3:8b",   "qwen2.5-coder:7b"),
    "16gb": ("qwen3:14b",  "qwen2.5-coder:14b"),
    "32gb": ("qwen3:32b",  "qwen3-coder:30b"),
}

SCRIPTS = ["sysmind.py", "sysmind_scan.py", "sysmind_orbit.py", "sysmind_display.py",
           "sysmind_common.py", "sysmind_doctor.py", "sysmind_partners.py",
           "sysmind_sync.py", "sysmind_turn.py"]


def ask(question: str, options: list, default: int = 0) -> int:
    print(f"\n{question}")
    for i, opt in enumerate(options):
        marker = " (default)" if i == default else ""
        print(f"  [{i+1}] {opt}{marker}")
    ans = input("Choice: ").strip()
    if not ans:
        return default
    try:
        idx = int(ans) - 1
        if 0 <= idx < len(options):
            return idx
    except ValueError:
        pass
    print("Invalid choice, using default.")
    return default


def detect_ram() -> str:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    gb = kb / 1024 / 1024
                    if gb < 5:
                        return "4gb"
                    elif gb < 12:
                        return "8gb"
                    elif gb < 24:
                        return "16gb"
                    else:
                        return "32gb"
    except Exception:
        pass
    return "8gb"


def create_wrapper(name: str, script_name: str) -> None:
    """Create a shell wrapper in ~/.local/bin/ that calls the Python script."""
    wrapper = BIN_DIR / name
    content = f'''#!/bin/bash
export PYTHONPATH="{LIB_DIR}:$PYTHONPATH"
exec python3 "{LIB_DIR / script_name}" "$@"
'''
    with open(wrapper, "w") as f:
        f.write(content)
    os.chmod(wrapper, 0o755)
    print(f"Installed wrapper: {wrapper}")


def install():
    print("🧠 Sysmind Installer")
    print("=" * 40)

    level_idx = ask("How hands-off do you want this?", [
        "Advisor — AI explains, I run everything manually",
        "Assistant — AI suggests, I approve before running",
        "Autopilot — Safe stuff auto-runs, dangerous asks",
        "Full Auto — System self-manages, alerts only",
    ], default=1)
    level = level_idx + 1

    ram = detect_ram()
    tiers = ["4gb", "8gb", "16gb", "32gb"]
    ram_options = [
        "4GB or less  - qwen3:1.7b + qwen2.5-coder:1.5b",
        "8GB          - qwen3:8b + qwen2.5-coder:7b",
        "16GB         - qwen3:14b + qwen2.5-coder:14b",
        "24GB or more - qwen3:32b + qwen3-coder:30b",
    ]
    ram_idx = ask("How much RAM does this machine have?", ram_options,
                  default=tiers.index(ram) if ram in tiers else 1)
    ram_tier = tiers[ram_idx]
    conscious_model, unconscious_model = MODEL_PAIRS[ram_tier]
    budgets = {"4gb": 2000, "8gb": 4000, "16gb": 8000, "32gb": 8000}

    print(f"\n  conscious slot (your language): {conscious_model}")
    print(f"  unconscious slot (shell):       {unconscious_model}")
    if ram_tier in ("4gb", "8gb"):
        print("  note: two models on this much RAM is tight. Ollama swaps them")
        print("        on demand, or point one slot at an API endpoint in")
        print("        config.json (backend: openai, base_url, api_key_env).")

    lang_idx = ask("Preferred reply language?", [
        "Auto — match the language I type in",
        "English",
        "Urdu",
        "Other (I'll edit config later)",
    ], default=0)
    language = ["auto", "English", "Urdu", "auto"][lang_idx]

    paranoia_idx = ask("Security scan depth?", ["Low", "Medium", "High"], default=1)
    paranoia = ["low", "medium", "high"][paranoia_idx]

    notif_idx = ask("Desktop notifications?", ["Native popups", "Terminal only", "None"], default=0)
    notifications = ["native", "terminal", "none"][notif_idx]

    launch_idx = ask("Launch method?", ["sysmind command", "Hotkey (requires setup)", "Both"], default=0)
    launch = ["alias", "hotkey", "both"][launch_idx]

    blocklist_idx = ask("Block destructive commands?", ["Yes — block rm/dd/mkfs (safe)", "No — allow anything (expert)"], default=0)
    blocklist_enabled = blocklist_idx == 0

    config = {
        "level": level,
        "ram_tier": ram_tier,
        "slots": {
            "conscious": {"backend": "ollama", "model": conscious_model},
            "unconscious": {"backend": "ollama", "model": unconscious_model},
        },
        "model": conscious_model,   # legacy key, kept for older readers
        "budget": budgets[ram_tier],
        "language": language,
        "paranoia": paranoia,
        "notifications": notifications,
        "launch_method": launch,
        "display_dashboard": level >= 3,
        "blocklist_enabled": blocklist_enabled,
    }

    # Create dirs
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)

    # Write config
    with open(CONFIG_DIR / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    # Copy scripts to lib dir
    for script in SCRIPTS:
        src = PROJECT_ROOT / script
        if src.exists():
            dst = LIB_DIR / script
            shutil.copy2(src, dst)
            print(f"Installed: {dst}")

    # Create wrappers
    create_wrapper("sysmind", "sysmind.py")
    create_wrapper("sysmind-scan", "sysmind_scan.py")
    create_wrapper("sysmind-orbit", "sysmind_orbit.py")
    create_wrapper("sysmind-display", "sysmind_display.py")
    create_wrapper("sysmind-doctor", "sysmind_doctor.py")
    create_wrapper("sysmind-sync", "sysmind_sync.py")

    # Shell alias / PATH
    shell_rc = None
    shell = os.environ.get("SHELL", "")
    if "bash" in shell:
        shell_rc = Path.home() / ".bashrc"
    elif "zsh" in shell:
        shell_rc = Path.home() / ".zshrc"

    if shell_rc and shell_rc.exists():
        path_line = 'export PATH="$HOME/.local/bin:$PATH"\n'
        with open(shell_rc, "r") as f:
            existing = f.read()
        if path_line.strip() not in existing:
            with open(shell_rc, "a") as f:
                f.write(f"\n# sysmind\n{path_line}")
            print(f"Added PATH to {shell_rc}")

    # Cron for Level 3-4
    if level >= 3:
        cron_line = f"0 * * * * {BIN_DIR}/sysmind-scan {paranoia} > /dev/null 2>&1\n"
        try:
            r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            existing = r.stdout if r.returncode == 0 else ""
            if "sysmind-scan" not in existing:
                new_cron = existing + cron_line
                subprocess.run(["crontab", "-"], input=new_cron, text=True, check=True)
                print("Added hourly scan to crontab.")
        except Exception as e:
            print(f"Could not set up cron: {e}")

    # Check/install Ollama
    ollama_found = shutil.which("ollama") is not None
    if not ollama_found:
        print("\n⚠️  Ollama not found.")
        print("Install it from: https://ollama.com/download/linux")
        print(f"Then: ollama pull {conscious_model} && ollama pull {unconscious_model}")
    else:
        for m in (conscious_model, unconscious_model):
            print(f"\nPulling {m} ...")
            subprocess.run(["ollama", "pull", m])

    print("\n" + "=" * 40)
    print("Installation complete!")
    print(f"Config: {CONFIG_DIR / 'config.json'}")
    print(f"Scripts: {LIB_DIR}")
    print(f"Wrappers: {BIN_DIR}")
    print("\nCalibrate the pair before first use:  sysmind-sync calibrate")
    if shell_rc:
        print(f"\nRun: source {shell_rc} && sysmind")
    else:
        print(f"\nRun: export PATH=\"$HOME/.local/bin:$PATH\" && sysmind")


if __name__ == "__main__":
    install()
