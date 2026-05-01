#!/bin/bash
set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo ">>> DRY-RUN: Es werden keine Änderungen gepusht."
fi

# Apache-2.0 Lizenztext herunterladen
LICENSE_FILE="$(mktemp)"
trap 'rm -f "$LICENSE_FILE"' EXIT

echo "Lade Apache-2.0 Lizenztext..."
curl -sf https://api.github.com/licenses/apache-2.0 | jq -r '.body' > "$LICENSE_FILE"

if [[ ! -s "$LICENSE_FILE" ]]; then
  echo "FEHLER: Lizenztext konnte nicht geladen werden." >&2
  exit 1
fi

# Repos ohne Lizenz abrufen (licenseInfo muss in --json enthalten sein)
echo "Rufe Repositories ohne Lizenz ab..."
repos=$(gh repo list --visibility=public --no-archived --limit 150 \
  --json name,owner,licenseInfo \
  --jq '.[] | select(.licenseInfo == null) | "\(.owner.login)/\(.name)"')

if [[ -z "$repos" ]]; then
  echo "Keine Repositories ohne Lizenz gefunden."
  exit 0
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"; rm -f "$LICENSE_FILE"' EXIT

echo "$repos" | while IFS= read -r repo_full; do
  echo "-----------------------------------------------"
  echo "Bearbeite: $repo_full"

  repo_dir="$WORK_DIR/repo"
  rm -rf "$repo_dir"

  # Shallow clone, um vorhandenen Inhalt zu erhalten
  if ! git clone --quiet --depth=1 "https://github.com/${repo_full}.git" "$repo_dir"; then
    echo "WARNUNG: Clone fehlgeschlagen für $repo_full – übersprungen." >&2
    continue
  fi

  # Prüfen ob LICENSE bereits vorhanden (unabhängig vom API-Filter)
  if [[ -f "$repo_dir/LICENSE" || -f "$repo_dir/LICENSE.txt" || -f "$repo_dir/LICENSE.md" ]]; then
    echo "  LICENSE bereits vorhanden – übersprungen."
    continue
  fi

  cp "$LICENSE_FILE" "$repo_dir/LICENSE"

  (
    cd "$repo_dir"
    git add LICENSE
    git commit --quiet -m "docs: add Apache-2.0 license"

    if [[ "$DRY_RUN" == true ]]; then
      echo "  [DRY-RUN] Push würde jetzt erfolgen."
    else
      if ! git push origin HEAD; then
        echo "WARNUNG: Push fehlgeschlagen für $repo_full" >&2
      else
        echo "  Lizenz erfolgreich hinzugefügt."
      fi
    fi
  )
done

echo "-----------------------------------------------"
echo "Fertig."
