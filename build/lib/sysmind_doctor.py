"""Pre-install diagnostics for sysmind."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from sysmind_common import run_cmd


def check(cmd: list, label: str) -> tuple:
    """Run a command, return (ok, message)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if r.returncode == 0:
            return True, r.stdout.strip()
        return False, r.stderr.strip() or "not found"
    except Exception as e:
        return False, str(e)


def ram_tier() -> str:
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
    return "unknown"


def models_for_tier(tier: str) -> list:
    return {
        "4gb": ["qwen3:1.7b", "qwen2.5-coder:1.5b"],
        "8gb": ["qwen3:8b", "qwen2.5-coder:7b"],
        "16gb": ["qwen3:14b", "qwen2.5-coder:14b"],
        "32gb": ["qwen3:32b", "qwen3-coder:30b", "qwen2.5-coder:32b"],
        "unknown": ["qwen3:8b"],
    }.get(tier, ["qwen3:8b"])


def main():
    print("🩺 Sysmind Doctor")
    print("=" * 50)
    
    issues = 0
    warnings = 0
    
    # 1. Python version
    ver = sys.version_info
    ok = ver.major == 3 and ver.minor >= 8
    if ok:
        print(f"✅ Python {ver.major}.{ver.minor}.{ver.micro}")
    else:
        print(f"❌ Python {ver.major}.{ver.minor}.{ver.micro} — need 3.8+")
        issues += 1
    
    # 2. OS
    ok, os_name = check(["uname", "-s"], "OS")
    if ok and os_name == "Linux":
        print(f"✅ OS: Linux")
    elif ok:
        print(f"⚠️  OS: {os_name} — sysmind is designed for Linux")
        warnings += 1
    else:
        print(f"❌ Cannot detect OS")
        issues += 1
    
    # 3. Distro
    ok, pretty = check(["cat", "/etc/os-release"], "distro")
    if ok and "parrot" in pretty.lower():
        print(f"✅ Distro: Parrot OS detected")
    elif ok and "debian" in pretty.lower():
        print(f"✅ Distro: Debian-based")
    elif ok and "ubuntu" in pretty.lower():
        print(f"✅ Distro: Ubuntu-based")
    elif ok:
        pretty_name = next((l.split("=", 1)[1].strip('"') for l in pretty.splitlines() if l.startswith("PRETTY_NAME")), "unknown")
        print(f"⚠️  Distro: {pretty_name} — may work, not tested")
        warnings += 1
    else:
        print(f"⚠️  Cannot read /etc/os-release")
        warnings += 1
    
    # 4. RAM
    tier = ram_tier()
    if tier == "4gb":
        print(f"⚠️  RAM: ~4GB — use qwen3:1.7b (balanced, decent Urdu) or qwen2.5-coder:1.5b (limited)")
        warnings += 1
    elif tier == "8gb":
        print(f"✅ RAM: ~8GB — sweet spot for qwen3:8b (strong shell + Urdu)")
    elif tier == "16gb":
        print(f"✅ RAM: 16GB — run qwen3:14b (balanced) or qwen2.5-coder:14b (ops-first)")
    elif tier == "32gb":
        print(f"✅ RAM: 24GB+ — run qwen3:32b or qwen3-coder:30b (MoE, ~7B-class speed)")
    else:
        print(f"⚠️  RAM: unknown — cannot read /proc/meminfo")
        warnings += 1
    
    # 5. Disk space
    ok, df = check(["df", "-h", "/"], "disk")
    if ok:
        parts = df.splitlines()[-1].split()
        avail = parts[3]
        pct = int(parts[4].rstrip("%"))
        if pct > 90:
            print(f"❌ Disk: {pct}% full ({avail} free) — need space for models (~5GB)")
            issues += 1
        elif pct > 70:
            print(f"⚠️  Disk: {pct}% full ({avail} free) — models need ~5GB")
            warnings += 1
        else:
            print(f"✅ Disk: {pct}% full ({avail} free)")
    else:
        print(f"⚠️  Disk: cannot check")
        warnings += 1
    
    # 6. Ollama installed
    ollama_path = shutil.which("ollama")
    if ollama_path:
        print(f"✅ Ollama: {ollama_path}")
    else:
        print(f"❌ Ollama: not found")
        print(f"   Fix: curl -fsSL https://ollama.com/install.sh | sh")
        issues += 1
    
    # 7. Ollama running
    if ollama_path:
        ok, _ = check(["ollama", "list"], "ollama running")
        if ok:
            print(f"✅ Ollama: daemon responding")
        else:
            print(f"❌ Ollama: installed but daemon not running")
            print(f"   Fix: ollama serve &")
            issues += 1
    
    # 8. Models available
    if ollama_path:
        ok, models_out = check(["ollama", "list"], "models")
        if ok:
            installed = [l.split()[0] for l in models_out.splitlines()[1:] if l.strip()]
            recommended = models_for_tier(tier)
            found = [m for m in recommended if m in installed]
            if found:
                print(f"✅ Models: {', '.join(found)} installed")
            else:
                print(f"⚠️  Models: none of the recommended models installed")
                print(f"   Recommended for {tier}: {', '.join(recommended)}")
                print(f"   Fix: ollama pull {recommended[0]}")
                warnings += 1
        else:
            print(f"⚠️  Models: cannot list (daemon may not be running)")
            warnings += 1
    
    # 9. Required commands
    required = ["apt", "systemctl", "journalctl", "ss", "ufw", "last", "free", "df"]
    missing = []
    for cmd in required:
        if not shutil.which(cmd):
            missing.append(cmd)
    if missing:
        print(f"⚠️  Missing commands: {', '.join(missing)}")
        print(f"   sysmind-scan will skip these sections")
        warnings += 1
    else:
        print(f"✅ Core commands: all present")
    
    # 10. Displays
    ok, xrandr = check(["xrandr", "--listmonitors"], "displays")
    if ok:
        count = len(xrandr.splitlines()) - 1
        if count >= 2:
            print(f"✅ Displays: {count} detected (dual-display ready)")
        else:
            print(f"⚠️  Displays: {count} detected (single display)")
            warnings += 1
    else:
        print(f"⚠️  Displays: cannot detect (xrandr not available)")
        warnings += 1
    
    # 11. Existing sysmind config
    config_file = Path.home() / ".config" / "sysmind" / "config.json"
    if config_file.exists():
        try:
            with open(config_file) as f:
                cfg = json.load(f)
            level = cfg.get("level", "?")
            model = cfg.get("model", "?")
            print(f"✅ Config: existing install found (level {level}, {model})")
        except Exception:
            print(f"⚠️  Config: file exists but unreadable")
            warnings += 1
    else:
        print(f"ℹ️  Config: no existing install")
    
    # Summary
    print("=" * 50)
    if issues == 0 and warnings == 0:
        print("🟢 All clear — ready to install")
    elif issues == 0:
        print(f"🟡 {warnings} warning(s) — should work, review above")
    else:
        print(f"🔴 {issues} issue(s), {warnings} warning(s) — fix issues before installing")
    
    if issues > 0 or warnings > 0:
        print(f"\nRun: python3 install.py")
        print(f"(installer will guide through setup)")


if __name__ == "__main__":
    main()
