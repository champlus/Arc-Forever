#!/bin/bash
set -u
cd -- "$(dirname -- "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
    echo "Arc Forever requires Python 3 and Apple Command Line Tools."
    read -r -p "Press Return to close. " unused
    exit 1
fi

if [ "$#" -gt 0 ]; then
    exec python3 arc_forever.py "$@"
fi

echo "=================================================="
echo "  Arc Forever — Keep Arc Browser Alive on macOS"
echo "=================================================="
python3 arc_forever.py status 2>/dev/null || true
echo "--------------------------------------------------"
echo "  Please quit Arc before applying or restoring."
echo ""
echo "  1) Apply Patch"
echo "  2) Restore Original Arc"
echo "  3) Check Status"
echo "  4) Exit"
echo ""
read -r -p "Select an option [1-4]: " choice
echo ""
case "$choice" in
    1) python3 arc_forever.py apply ;;
    2) python3 arc_forever.py restore ;;
    3) python3 arc_forever.py status ;;
    *) exit 0 ;;
esac
result=$?
echo ""
read -r -p "Press Return to close. " unused
exit "$result"
