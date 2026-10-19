#!/bin/sh
# Thin harness over the reusable reader and Rust library; no independent conversion logic.
set -eu
if [ "$#" -ne 2 ]; then
    echo 'Usage: scripts/import-aaf.sh INPUT.aaf NEW_OUTPUT_DIRECTORY' >&2
    exit 2
fi
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python_bin=${SOUNDCRAFT_PYTHON:-"$project_dir/.venv/bin/python"}
plan_file=$(mktemp "${TMPDIR:-/tmp}/soundcraft-plan.XXXXXX")
# Python opens exclusively, so reserve only a name here.
rm -- "$plan_file"
trap 'rm -f -- "$plan_file"' EXIT HUP INT TERM
PYTHONPATH="$project_dir/python" "$python_bin" -m soundcraft_aaf "$1" "$plan_file"
"$project_dir/target/debug/plan-to-session" "$plan_file" "$2"
