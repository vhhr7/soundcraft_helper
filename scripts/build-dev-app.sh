#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"
./scripts/apply-ui-overlay.sh
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install --require-hashes -r requirements.txt
export CARGO_TARGET_DIR="$project_dir/local-build/target"
export CARGO_INCREMENTAL=0
cd upstream
cargo +1.95.0 build --locked -p soundcraft
cd "$project_dir"
python3 scripts/package-dev-app.py
