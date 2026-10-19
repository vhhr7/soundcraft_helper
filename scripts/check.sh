#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"
cargo fmt -- --check
cargo clippy --locked --all-targets -- -D warnings
cargo build --locked
cargo test --locked
PYTHONPATH=python .venv/bin/python -m unittest discover -s tests -v
