#!/bin/bash

mod_dir="$(cd "$(dirname "$0")" && pwd)" || exit 1

# Stop any instance left over from a previous launch.
if pkill -f -- "$mod_dir/main.py" 2>/dev/null; then
	echo "existing process was killed"
fi

cd "$mod_dir" || exit 1

# main.py exits by itself when the game closes, so no copy is left behind.
./venv/bin/python "$mod_dir/main.py" &
