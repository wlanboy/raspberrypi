#!/bin/bash

# --- KONFIGURATION ---
GITEA_URL="https://git.gmk.lan:3300"
GITEA_ORG="github"
GITEA_TOKEN="DEIN_GITEA_INTERNAL_TOKEN" # In Gitea unter Einstellungen > Anwendungen erstellt

GH_USER="DEIN_GITHUB_USERNAME"
GH_PAT="DEIN_GITHUB_PERSONAL_ACCESS_TOKEN"

# --- SCRIPT-START ---

echo "--- Starte Update der Push-Mirrors für Organisation: $GITEA_ORG ---"

# 1. Alle Repositories der Organisation abrufen
# Wir nutzen jq, um die Namen der Repos aus der JSON-Antwort zu extrahieren
REPOS=$(curl -s -H "Authorization: token $GITEA_TOKEN" \
    "$GITEA_URL/api/v1/orgs/$GITEA_ORG/repos" | jq -r '.[].name')

if [ -z "$REPOS" ] || [ "$REPOS" == "null" ]; then
    echo "Fehler: Keine Repositories gefunden oder API-Verbindung fehlgeschlagen."
    exit 1
fi

for REPO in $REPOS; do
    echo "Bearbeite Repo: $REPO..."

    # 2. Push-Mirror Adresse aktualisieren
    # Wir setzen die URL im Format https://user:token@github.com/...
    RESPONSE=$(curl -s -X PATCH \
        "$GITEA_URL/api/v1/repos/$GITEA_ORG/$REPO/push_mirrors" \
        -H "accept: application/json" \
        -H "Content-Type: application/json" \
        -H "Authorization: token $GITEA_TOKEN" \
        -d "{
          \"remote_address\": \"https://$GH_USER:$GH_PAT@github.com/$GH_USER/$REPO.git\"
        }")

    # Kurze Prüfung, ob der Patch erfolgreich war (Gitea gibt ein Array/Objekt zurück)
    if [[ $RESPONSE == *"remote_address"* ]]; then
        echo "  [OK] Credentials aktualisiert."
        
        # 3. Optional: Sofortigen Sync anstoßen
        curl -s -X POST "$GITEA_URL/api/v1/repos/$GITEA_ORG/$REPO/mirror-sync" \
            -H "Authorization: token $GITEA_TOKEN" > /dev/null
        echo "  [OK] Sync-Vorgang gestartet."
    else
        echo "  [FEHLER] Konnte Credentials für $REPO nicht aktualisieren."
        echo "  Antwort: $RESPONSE"
    fi
    
    echo "-----------------------------------------------"
done

echo "Fertig!"