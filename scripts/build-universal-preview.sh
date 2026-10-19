#!/bin/sh
# Local, ad-hoc signed development DMG. Does not notarize, install or publish.
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_dir=${SOUNDCRAFT_SOURCE_DIR:-"$project_dir/local-build/upstream-contribution"}
build_dir=${SOUNDCRAFT_BUILD_DIR:-"$project_dir/local-build/universal-target"}
dist_dir="$project_dir/local-build/dist"
app="$dist_dir/SoundCraft AAF Preview-dev.2.app"
dmg="$dist_dir/soundcraft-aaf-preview-0.9.0-aaf.1-dev.2-macos-universal.dmg"
if [ -e "$app" ] || [ -e "$dmg" ]; then
    echo 'Output already exists; choose a new version/output before rebuilding.' >&2
    exit 1
fi
mkdir -p "$build_dir"
python3 - "$build_dir" <<'PY'
import shutil,sys
free=shutil.disk_usage(sys.argv[1]).free
if free < 12*1024**3:
    raise SystemExit(f'Need at least 12 GiB free on the build volume; currently {free/1024**3:.1f} GiB. Set SOUNDCRAFT_BUILD_DIR to an external volume if needed.')
PY
if [ "${1:-}" = '--check' ]; then exit 0; fi
if [ ! -f "$source_dir/crates/interchange/src/lib.rs" ]; then
    echo 'Prepare the independent contribution checkout with scripts/export-upstream.py --checkout local-build/upstream-contribution' >&2
    exit 1
fi
cd "$project_dir"
python3 scripts/prepare-python-runtime.py arm64
python3 scripts/prepare-python-runtime.py x86_64
.venv/bin/python -m pip download --require-hashes --only-binary=:all: --no-deps --dest local-build/downloads -r requirements.txt
rustup target add --toolchain 1.95.0 aarch64-apple-darwin x86_64-apple-darwin
export MACOSX_DEPLOYMENT_TARGET=11.0
export CARGO_TARGET_DIR="$build_dir"
export CARGO_INCREMENTAL=0
(cd "$source_dir" && cargo +1.95.0 build --locked --release -p soundcraft --target aarch64-apple-darwin --target x86_64-apple-darwin)
mkdir -p local-build/universal-fat "$dist_dir"
for target in aarch64-apple-darwin x86_64-apple-darwin; do
    rustc +1.95.0 --edition 2024 --target "$target" -O packaging/preview-launcher.rs -o "local-build/universal-fat/launcher-$target"
done
lipo -create "$build_dir/aarch64-apple-darwin/release/soundcraft" "$build_dir/x86_64-apple-darwin/release/soundcraft" -output local-build/universal-fat/SoundCraft-bin
lipo -create local-build/universal-fat/launcher-aarch64-apple-darwin local-build/universal-fat/launcher-x86_64-apple-darwin -output local-build/universal-fat/SoundCraftAAF
python3 scripts/package-portable-preview.py --binary local-build/universal-fat/SoundCraft-bin --launcher local-build/universal-fat/SoundCraftAAF --output "$app" --architectures arm64 x86_64
# Ad-hoc signatures only. Developer ID and notarization are separate release gates.
codesign --force --sign - "$app/Contents/MacOS/SoundCraft-bin"
codesign --force --sign - "$app/Contents/MacOS/SoundCraftAAF"
codesign --force --sign - "$app"
codesign --verify --strict --deep --verbose=2 "$app"
"$app/Contents/MacOS/SoundCraftAAF" --reader-self-test
codesign --verify --strict --deep --verbose=2 "$app"
stage=$(mktemp -d "$dist_dir/dmg-stage.XXXXXX")
ditto "$app" "$stage/SoundCraft AAF Preview.app"
ln -s /Applications "$stage/Applications"
mkdir "$stage/Demo AAF"
for name in 'Montaje sintético.aaf' 'Diálogo á #1.wav' 'Ambiente estéreo.wav'; do
    cp "$project_dir/demo/AAF con espacios ñ/$name" "$stage/Demo AAF/$name"
done
cp "$project_dir/LICENSE" "$stage/Demo AAF/LICENSE.txt"
cp "$project_dir/packaging/demo-readme.txt" "$stage/Demo AAF/LEEME.txt"
hdiutil create -srcfolder "$stage" -volname 'SoundCraft AAF Preview' -format UDZO "$dmg"
hdiutil verify "$dmg"
(cd "$dist_dir" && shasum -a 256 "$(basename "$dmg")" > "$(basename "$dmg").sha256")
echo "Development DMG prepared: $dmg"
echo 'Not a validated RC: Intel hardware, clean-install, listening, long-session, Developer ID and notarization checks remain.'
