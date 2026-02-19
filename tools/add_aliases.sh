#!/bin/bash

BASHRC="$HOME/.bashrc"

declare -A ALIASES=(
    ["gu"]="python3 ~/git/raspberrypi/tools/git_pull_all.py ~/git"
    ["gm"]="python3 ~/git/raspberrypi/tools/mirror_git_repos.py ~/git"
    ["gs"]="python3 ~/git/raspberrypi/tools/git_status_all.py ~/git"
    ["gl"]="python3 ~/git/raspberrypi/tools/scan_git_repos.py ~/git"
)

FORCE=0
if [ "$1" = "-f" ]; then
    FORCE=1
fi

added=0

for name in "${!ALIASES[@]}"; do
    cmd="${ALIASES[$name]}"
    if grep -q "alias ${name}=" "$BASHRC" 2>/dev/null; then
        if [ "$FORCE" -eq 1 ]; then
            sed -i "/alias ${name}=/d" "$BASHRC"
            echo "alias ${name}='${cmd}'" >> "$BASHRC"
            echo "Alias '$name' overwritten."
            ((added++))
        else
            echo "Alias '$name' already exists, skipping."
        fi
    else
        echo "alias ${name}='${cmd}'" >> "$BASHRC"
        echo "Alias '$name' added."
        ((added++))
    fi
done

if [ "$added" -gt 0 ]; then
    echo ""
    echo "$added alias(es) added. Run 'source ~/.bashrc' to apply."
fi
