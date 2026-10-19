#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir/upstream"
base=25d52c646aea780c8076ff966076f994ad256221
if [ "$(git rev-parse HEAD)" != "$base" ]; then
    echo "Expected SoundCraft base $base. Refusing to change another revision." >&2
    exit 1
fi
if git apply --reverse --check "$project_dir/integration/soundcraft-aaf.patch" 2>/dev/null; then
    echo "AAF development overlay already applied."
else
    git apply --check "$project_dir/integration/soundcraft-aaf.patch"
    git apply "$project_dir/integration/soundcraft-aaf.patch"
fi
