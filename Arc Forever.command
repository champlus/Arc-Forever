#!/bin/bash
set -u
cd -- "$(dirname -- "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
    echo 'Arc Forever requires Python 3 and Apple Command Line Tools.'
    read -r -p 'Press Return to close. ' unused
    exit 1
fi

if [ "$#" -gt 0 ]; then
    exec python3 arc_forever.py "$@"
fi

echo 'Arc Forever — original Arc, local authentication, reversible patch'
echo 'Quit Arc before applying or restoring. / 修改或恢复前请退出 Arc。'
echo '1. Apply / 原地修改'
echo '2. Restore / 恢复原版'
echo '3. Status / 查看状态'
echo '4. Exit / 退出'
read -r -p 'Choose / 选择 [1-4]: ' choice
case "$choice" in
    1) python3 arc_forever.py apply ;;
    2) python3 arc_forever.py restore ;;
    3) python3 arc_forever.py status ;;
    *) exit 0 ;;
esac
result=$?
read -r -p 'Press Return to close / 回车关闭。' unused
exit "$result"
