#!/bin/bash
# Downloads OpenVINO models from HuggingFace into OVMS-compatible directory structure:
# /data/openvino/<model-name>/1/<model-files>
set -euo pipefail

MODELS_DIR="/data/openvino"
MIN_FREE_GB=30

# HuggingFace repo -> local model name
declare -A MODELS=(
    ["qwen3-8b-int4-cw-ov"]="OpenVINO/Qwen3-8B-int4-cw-ov"
    ["whisper-small-int8-ov"]="OpenVINO/whisper-small-int8-ov"
    ["whisper-medium-en-int8-ov"]="OpenVINO/whisper-medium.en-int8-ov"
    ["gemma-4-e4b-it-int4-ov"]="OpenVINO/gemma-4-E4B-it-int4-ov"
)

# Approximate download sizes in GB for display
declare -A SIZES=(
    ["qwen3-8b-int4-cw-ov"]="9.5"
    ["whisper-small-int8-ov"]="0.5"
    ["whisper-medium-en-int8-ov"]="1.5"
    ["gemma-4-e4b-it-int4-ov"]="6.5"
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }

check_dependencies() {
    if command -v hf &>/dev/null; then
        echo "hf"
        return
    fi
    if command -v huggingface-cli &>/dev/null; then
        echo "huggingface-cli"
        return
    fi
    if python3 -c "import huggingface_hub" &>/dev/null 2>&1; then
        echo "python3"
        return
    fi
    if command -v git &>/dev/null && git lfs version &>/dev/null 2>&1; then
        echo "git-lfs"
        return
    fi
    echo "none"
}

check_disk_space() {
    local target_dir="$1"
    local required_gb="$2"
    local parent_dir
    parent_dir=$(dirname "$target_dir")
    mkdir -p "$parent_dir"
    local free_gb
    free_gb=$(df -BG "$parent_dir" | awk 'NR==2 {gsub("G",""); print $4}')
    if [[ "$free_gb" -lt "$required_gb" ]]; then
        err "Nicht genug Speicherplatz: ${free_gb}GB frei, ${required_gb}GB benötigt in $parent_dir"
        exit 1
    fi
    log "Freier Speicher: ${free_gb}GB (benötigt: ~${required_gb}GB)"
}

download_with_hf() {
    local hf_repo="$1"
    local target_dir="$2"
    hf download "$hf_repo" \
        --local-dir "$target_dir" \
        --exclude "*.gitattributes" \
        --exclude "README.md"
}

download_with_hf_cli() {
    local hf_repo="$1"
    local target_dir="$2"
    huggingface-cli download "$hf_repo" \
        --local-dir "$target_dir" \
        --local-dir-use-symlinks False \
        --exclude "*.gitattributes" "README.md"
}

download_with_python() {
    local hf_repo="$1"
    local target_dir="$2"
    python3 - <<PYEOF
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="$hf_repo",
    local_dir="$target_dir",
    local_dir_use_symlinks=False,
    ignore_patterns=["*.gitattributes", "README.md"],
)
print("Download abgeschlossen.")
PYEOF
}

download_with_git_lfs() {
    local hf_repo="$1"
    local target_dir="$2"
    local tmp_dir="${target_dir}.tmp"
    GIT_LFS_SKIP_SMUDGE=0 git clone "https://huggingface.co/$hf_repo" "$tmp_dir"
    rsync -a --exclude='.git' --exclude='README.md' "$tmp_dir/" "$target_dir/"
    rm -rf "$tmp_dir"
}

download_model() {
    local model_name="$1"
    local hf_repo="$2"
    local size="${SIZES[$model_name]}"
    local target_dir="$MODELS_DIR/$model_name/1"

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    log "Modell:  $model_name"
    log "Quelle:  https://huggingface.co/$hf_repo"
    log "Ziel:    $target_dir"
    log "Größe:   ~${size}GB"

    # Skip if already downloaded (check for at least one .xml file)
    if compgen -G "$target_dir/*.xml" > /dev/null 2>&1; then
        warn "Bereits vorhanden – übersprungen. Löschen zum erneuten Download: rm -rf $target_dir"
        return 0
    fi

    mkdir -p "$target_dir"

    local method
    method=$(check_dependencies)

    case "$method" in
        "hf")
            log "Download via hf ..."
            download_with_hf "$hf_repo" "$target_dir"
            ;;
        "huggingface-cli")
            log "Download via huggingface-cli ..."
            download_with_hf_cli "$hf_repo" "$target_dir"
            ;;
        "python3")
            log "Download via huggingface_hub (Python) ..."
            download_with_python "$hf_repo" "$target_dir"
            ;;
        "git-lfs")
            log "Download via git + LFS ..."
            download_with_git_lfs "$hf_repo" "$target_dir"
            ;;
        *)
            err "Kein Download-Tool gefunden. Bitte eines installieren:"
            err "  pip3 install huggingface_hub huggingface_hub[cli]"
            err "  oder: sudo apt install git-lfs && git lfs install"
            exit 1
            ;;
    esac

    # Verify download: at least one .xml must exist
    if ! compgen -G "$target_dir/*.xml" > /dev/null 2>&1; then
        err "Download fehlgeschlagen – keine .xml Dateien in $target_dir"
        exit 1
    fi

    local file_count
    file_count=$(find "$target_dir" -type f | wc -l)
    log "Fertig: $file_count Dateien in $target_dir"
}

print_structure() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    log "Verzeichnisstruktur unter $MODELS_DIR:"
    echo ""
    find "$MODELS_DIR" -maxdepth 3 \( -name "*.xml" -o -name "*.json" \) \
        | sort \
        | sed "s|$MODELS_DIR/||" \
        | awk -F'/' '{
            if ($1 != prev1) { print "  " $1 "/"; prev1=$1 }
            if ($2 != prev2) { print "    " $2 "/"; prev2=$2 }
            print "      " $3
          }'
}

# ── Main ──────────────────────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     OpenVINO Model Server – Modell-Download          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

log "Zielverzeichnis: $MODELS_DIR"
check_disk_space "$MODELS_DIR" "$MIN_FREE_GB"

# Allow downloading a single model: ./loadmodels.sh qwen3-8b-int4-cw-ov
if [[ $# -gt 0 ]]; then
    model_name="$1"
    if [[ -z "${MODELS[$model_name]+_}" ]]; then
        err "Unbekanntes Modell: $model_name"
        echo "Verfügbare Modelle:"
        for m in "${!MODELS[@]}"; do echo "  $m"; done | sort
        exit 1
    fi
    download_model "$model_name" "${MODELS[$model_name]}"
else
    for model_name in $(echo "${!MODELS[@]}" | tr ' ' '\n' | sort); do
        download_model "$model_name" "${MODELS[$model_name]}"
    done
fi

print_structure

echo ""
log "Alle Modelle bereit. OVMS starten:"
echo ""
echo "  docker run -d --name ovms \\"
echo "    -u \$(id -u) \\"
echo "    -v $MODELS_DIR:/models \\"
echo "    -p 9000:9000 -p 8080:8080 \\"
echo "    --restart unless-stopped \\"
echo "    openvino/model_server:latest \\"
echo "    --config_path /models/config.json \\"
echo "    --port 9000 --rest_port 8080"
echo ""
