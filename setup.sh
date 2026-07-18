#!/usr/bin/env bash
# Sysmind one-command setup: health check, then guided install.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

echo "🧠 Sysmind Setup"
echo "================"
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 not found. Install it first:  sudo apt install python3"
    exit 1
fi

# 1. Health check
python3 sysmind_doctor.py || true
echo

# 2. Stop on red (issues), warn-and-continue on yellow
read -r -p "Continue to install? [Y/n] " ans
case "${ans:-y}" in
    [nN]*) echo "Aborted. Fix the issues above and re-run ./setup.sh"; exit 0 ;;
esac

# 3. Run the guided installer
python3 install.py
