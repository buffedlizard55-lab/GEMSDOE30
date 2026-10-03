#!/usr/bin/env bash
# Competition training files are behind the DrivenData account wall. This script
# deliberately does not scrape the site, store credentials, or attempt a bypass.
# Put files downloaded through an authorized session in data/raw/ and rerun it.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${GEMS_DATA_DIR:-$ROOT/data/raw}"
REQUIRED=(training_features.tif labels.tif sample_submission.tif)
MISSING=()

for name in "${REQUIRED[@]}"; do
  if [[ ! -s "$DATA_DIR/$name" ]]; then
    MISSING+=("$name")
  fi
done

if ((${#MISSING[@]} == 0)); then
  echo "Competition data placement check passed: $DATA_DIR"
  printf '  %s\n' "${REQUIRED[@]}"
  exit 0
fi

printf 'Competition data not present in %s\n' "$DATA_DIR" >&2
printf 'Missing: %s\n' "${MISSING[*]}" >&2
cat >&2 <<'NOTICE'
The DrivenData competition data page redirects unauthenticated visitors to its
login page. This environment has no DrivenData session, and this repository will
not ask for or store passwords/cookies or bypass the access controls.

Download the files only through your own authorized competition account, then
place the official files in data/raw/ (or set GEMS_DATA_DIR). The expected names
come from this project's documented input contract; rename files locally only
after confirming their contents and metadata. Then run:
  python scripts/prepare_data.py
NOTICE
exit 2
