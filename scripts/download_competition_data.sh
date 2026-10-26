#!/usr/bin/env bash
set -euo pipefail

# Competition data preflight + autonomous pinned-mirror restoration for DOE GEMS.
# DrivenData's data page requires an authenticated participant session; this script
# never attempts login bypass, cookie scraping, or Dropbox credential handling.
# When files are absent and --check-only is NOT passed, it autonomously restores
# SHA-256-pinned owner mirrors via scripts/restore_public_mirrors.py when `gh`
# and Python are available, explicitly labelling them owner mirrors (not
# organizer-authenticated DrivenData downloads).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${GEMS_RAW_DATA_DIR:-${ROOT_DIR}/data/raw}"
CHECK_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-dir)
      DATA_DIR="$2"
      shift 2
      ;;
    --check-only)
      CHECK_ONLY=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage: scripts/download_competition_data.sh [--data-dir PATH] [--check-only]

Checks for (and, unless --check-only is passed, autonomously restores via SHA-256
pinned owner mirrors when `gh` is available) the official DOE GEMS competition
rasters in data/raw/:
  - training_features.tif   (Dropbox alias: gems-geodawn-numerical-features.tif)
  - labels.tif              (Dropbox alias: existing_faults.tif)
  - sample_submission.tif   (Dropbox alias: example_submission.tif)

Optional metadata (not required for 100 m raster training):
  - 1m_DEM_links.csv        (Dropbox alias: Digital-elevation-model-links-JSON.pdf)

Official DrivenData data page (login required for organizer-authenticated copy):
  https://www.drivendata.org/competitions/306/competition-doe-gems/data/
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "${DATA_DIR}"

PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python || true)"
fi

required=(
  "training_features.tif"
  "labels.tif"
  "sample_submission.tif"
)

missing=0
for name in "${required[@]}"; do
  if [[ ! -s "${DATA_DIR}/${name}" ]]; then
    missing=1
  fi
done

if [[ "${missing}" -eq 1 && "${CHECK_ONLY}" -eq 0 ]]; then
  if command -v gh >/dev/null 2>&1 && [[ -n "${PYTHON_BIN}" ]]; then
    echo "[restore] Missing raw competition rasters in ${DATA_DIR}; restoring SHA-256-pinned owner mirrors via gh api..."
    echo "[note] Restored files are hash-verified owner mirrors, NOT organizer-authenticated DrivenData downloads."
    "${PYTHON_BIN}" "${ROOT_DIR}/scripts/restore_public_mirrors.py" \
      --dest "${DATA_DIR}" \
      --ids training_features labels sample_submission
  fi
fi

missing=0
for name in "${required[@]}"; do
  if [[ -s "${DATA_DIR}/${name}" ]]; then
    echo "[ok] ${DATA_DIR}/${name}"
  else
    echo "[missing] ${DATA_DIR}/${name}" >&2
    missing=1
  fi
done

if [[ -s "${DATA_DIR}/1m_DEM_links.csv" ]]; then
  echo "[ok] ${DATA_DIR}/1m_DEM_links.csv (optional)"
else
  echo "[info] ${DATA_DIR}/1m_DEM_links.csv not present (optional)"
fi

if [[ "${missing}" -ne 0 ]]; then
  cat >&2 <<EOF

Competition data files are missing from ${DATA_DIR}.
Either sign in to DrivenData with an eligible account and download:
  https://www.drivendata.org/competitions/306/competition-doe-gems/data/
or run with authenticated GitHub CLI (gh) and Python so scripts/restore_public_mirrors.py
can restore the SHA-256-pinned owner mirrors, then run:
  python scripts/prepare_data.py --raw-dir "${DATA_DIR}"
EOF
  exit 2
fi

if [[ -n "${PYTHON_BIN}" && -f "${ROOT_DIR}/docs/research/mirror-pins.json" ]]; then
  "${PYTHON_BIN}" - "${DATA_DIR}" "${ROOT_DIR}/docs/research/mirror-pins.json" <<'PY'
import hashlib, json, pathlib, sys
data_dir = pathlib.Path(sys.argv[1])
pins = json.loads(pathlib.Path(sys.argv[2]).read_text())
for row in pins.get("files", []):
    if row.get("group") != "core":
        continue
    p = data_dir / row["dest"]
    if not p.is_file():
        continue
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    digest = h.hexdigest()
    if digest != row["sha256"]:
        raise SystemExit(f"[hash-mismatch] {p}: got {digest}, expected {row['sha256']}")
    print(f"[sha256-ok] {row['dest']} == {digest[:16]}...")
PY
fi

if [[ "${CHECK_ONLY}" -eq 0 ]]; then
  echo "All required competition rasters are present and SHA-256 verified. Next: python scripts/prepare_data.py"
fi
