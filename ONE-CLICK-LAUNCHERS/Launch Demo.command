#!/bin/sh
# macOS can open this file in Terminal; Linux can run: sh "Launch Demo.command"
cd -- "$(dirname -- "$0")" || exit 1
for candidate in python3.12 python3.11 python3.10 python3.13 python3.14 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(not ((3,10) <= sys.version_info[:2] <= (3,14)))' 2>/dev/null; then
        "$candidate" launch_demo.py "$@"
        demo_exit=$?
        if [ "$demo_exit" -ne 0 ] && [ -t 0 ]; then
            printf '\nPress Enter to close.'
            read -r demo_reply
        fi
        exit "$demo_exit"
    fi
done
printf '%s\n' 'Python 3.10 through 3.14 is needed (3.12 recommended).' 'Install it from https://www.python.org/downloads/ and run this launcher again.'
if [ -t 0 ]; then printf 'Press Enter to close.'; read -r demo_reply; fi
exit 1
