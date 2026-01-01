for d in */ ; do
  if [ -d "$d/.git" ]; then
    echo "===== Prüfe Git-Repo: $d ====="
    (
      cd "$d"
      git rev-list --objects --all \
        | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
        | awk '$3 > 50000 && $1 == "blob" {print $0}' \
        | sort -k3 -n
    )
    echo
  else
    echo "Überspringe $d (kein Git-Repo)"
  fi
done
