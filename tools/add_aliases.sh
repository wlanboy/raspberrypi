#!/bin/bash

BASHRC="$HOME/.bashrc"

declare -A ALIASES=(
    ["gu"]="python3 ~/git/raspberrypi/tools/git_pull_all.py ~/git"
    ["gm"]="python3 ~/git/raspberrypi/tools/mirror_git_repos.py ~/git"
    ["gitstatus"]="python3 ~/git/raspberrypi/tools/git_status_all.py ~/git"
    ["gitscan"]="python3 ~/git/raspberrypi/tools/scan_git_repos.py ~/git"
    ["gitnom"]="python3 ~/git/raspberrypi/tools/gh-no-mirror.py"
    ["up"]="python3 ~/git/raspberrypi/tools/update-pom.py"
    ["lp"]="python3 ~/git/raspberrypi/tools/local_push.py"
    ["hh"]="python3 -m http.server"
    ["dockerstatus"]="python3 ~/git/raspberrypi/tools/docker-image-status.py"
    ["dockerupdate"]="python3 ~/git/raspberrypi/tools/docker-image-update.py"
    ["updatestack"]="python3 ~/git/raspberrypi/tools/update-stack.py"
    ["aa"]="alias"
    ["giteaupdate"]="python3 ~/git/raspberrypi/tools/gitea-update-github-token.py"
    ["uu"]="uv lock --upgrade && uv pip compile pyproject.toml -o requirements.txt"
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
    echo "$added alias(es) added."
fi

source "$BASHRC"
echo "sourced $BASHRC"
