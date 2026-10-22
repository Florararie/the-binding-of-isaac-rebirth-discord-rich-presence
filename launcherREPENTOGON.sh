#!/bin/bash

mod_dir="$(cd "$(dirname "$0")" && pwd)" || exit 1

# Stop any instance left over from a previous launch.
if pkill -f -- "$mod_dir/main.py" 2>/dev/null; then
    echo "existing process was killed"
fi

cd "$mod_dir" || exit 1

# main.py watches both isaac-ng.exe and REPENTOGONLauncher.exe. It exits when
# the game closes (or, with REPENTOGON, when the launcher closes), so no copy
# is left running in the background.
./venv/bin/python "$mod_dir/main.py" &

args=("$@")

for i in "${!args[@]}"; do
    if [[ "${args[$i]}" == *"isaac-ng.exe" ]]; then
        args[$i]="${args[$i]/isaac-ng.exe/REPENTOGONLauncher/REPENTOGONLauncher.exe}"
    fi
done

exec "${args[@]}"
