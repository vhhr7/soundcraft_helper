#!/bin/sh
# Universal (arm64 + x86_64) development DMG built only from the contribution checkout.
# The AAF reader is pure Rust inside SoundCraft: no Python runtime, launcher or helper scripts.
# Ad-hoc signed. Does not notarize, install or publish anything.
set -eu
version=0.9.0-aaf.1-dev.3
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_dir=${SOUNDCRAFT_SOURCE_DIR:-"$project_dir/local-build/upstream-contribution"}
build_dir=${SOUNDCRAFT_BUILD_DIR:-"$project_dir/local-build/release-target"}
dist_dir="$project_dir/local-build/dist"
app="$dist_dir/SoundCraft AAF Preview-dev.3.app"
dmg="$dist_dir/soundcraft-aaf-preview-$version-macos-universal.dmg"
if [ -e "$app" ] || [ -e "$dmg" ]; then
    echo 'Output already exists; choose a new version before rebuilding.' >&2
    exit 1
fi
if ! grep -q 'pub fn read_aaf' "$source_dir/crates/interchange/src/aaf.rs" 2>/dev/null; then
    echo "The contribution checkout at $source_dir has no Rust AAF reader." >&2
    exit 1
fi
mkdir -p "$build_dir" "$dist_dir"
python3 - "$build_dir" <<'PY'
import shutil,sys
free=shutil.disk_usage(sys.argv[1]).free
if free < 6*1024**3:
    raise SystemExit(f'Need at least 6 GiB free on the build volume; currently {free/1024**3:.1f} GiB.')
PY
if [ "${1:-}" = '--check' ]; then exit 0; fi

export MACOSX_DEPLOYMENT_TARGET=11.0
export CARGO_TARGET_DIR="$build_dir"
export CARGO_INCREMENTAL=0
(cd "$source_dir" && cargo +1.95.0 build --locked --release -p soundcraft --target aarch64-apple-darwin --target x86_64-apple-darwin)

work=$(mktemp -d "$dist_dir/work-dev3.XXXXXX")
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources/Notices"
lipo -create "$build_dir/aarch64-apple-darwin/release/soundcraft" "$build_dir/x86_64-apple-darwin/release/soundcraft" \
    -output "$app/Contents/MacOS/SoundCraft"
lipo -info "$app/Contents/MacOS/SoundCraft"
cp "$source_dir/assets/app-icon/soundcraft.icns" "$app/Contents/Resources/SoundCraft.icns"
sha=$(git -C "$source_dir" rev-parse HEAD)
sed -e "s/@VERSION@/$version/g" -e "s/@SHORT_VERSION@/0.9.0/g" -e "s/@BUILD_SHA@/$sha/g" \
    "$source_dir/packaging/macos/Info.plist.in" >"$work/Info.plist"
# Separate name and bundle id so it never replaces or masquerades as an official SoundCraft.
# The .scraft type stays declared by the official app; this preview only opens it.
python3 - "$work/Info.plist" "$app/Contents/Info.plist" <<'PY'
import plistlib,sys
info=plistlib.load(open(sys.argv[1],'rb'))
info.update(CFBundleName='SoundCraft AAF Preview',CFBundleDisplayName='SoundCraft AAF Preview',
            CFBundleIdentifier='net.vicherrera.soundcraft.aaf-preview',CFBundleVersion='4')
info.pop('UTExportedTypeDeclarations',None)
plistlib.dump(info,open(sys.argv[2],'wb'))
PY
plutil -lint "$app/Contents/Info.plist"
printf 'APPL????' >"$app/Contents/PkgInfo"
for name in LICENSE-MIT LICENSE-APACHE NOTICE ATTRIBUTION.md; do
    cp "$source_dir/$name" "$app/Contents/Resources/Notices/SoundCraft-$name"
done
cp "$project_dir/LICENSE" "$app/Contents/Resources/Notices/soundcraft_helper-LICENSE"
cat >"$app/Contents/Resources/Notices/README.txt" <<EOF
Unofficial development preview of SoundCraft 0.9.0 with AAF session-data import.
Built from storytold/soundcraft 25d52c646aea780c8076ff966076f994ad256221 plus commit $sha
(vhhr7, branch feat/aaf-session-data). Pure Rust; the cfb crate (MIT) reads AAF containers.
Ad-hoc signed, not notarized. No Intel hardware or classroom validation is implied.
EOF

xattr -cr "$app"
codesign --force --sign - --timestamp=none --options runtime \
    --entitlements "$source_dir/packaging/macos/entitlements.plist" "$app/Contents/MacOS/SoundCraft"
codesign --force --sign - --timestamp=none --options runtime \
    --entitlements "$source_dir/packaging/macos/entitlements.plist" "$app"
codesign --verify --strict --deep --verbose=2 "$app"

stage="$work/stage"
mkdir -p "$stage/Demo AAF"
ditto "$app" "$stage/SoundCraft AAF Preview.app"
ln -s /Applications "$stage/Applications"
for name in 'Montaje sintético.aaf' 'Diálogo á #1.wav' 'Ambiente estéreo.wav'; do
    cp "$project_dir/demo/AAF con espacios ñ/$name" "$stage/Demo AAF/$name"
done
cp "$project_dir/LICENSE" "$stage/Demo AAF/LICENSE.txt"
cp "$project_dir/packaging/demo-readme.txt" "$stage/Demo AAF/LEEME.txt"
hdiutil create -srcfolder "$stage" -volname 'SoundCraft AAF Preview' -fs HFS+ -format UDZO -imagekey zlib-level=9 "$dmg"
hdiutil verify "$dmg"

mount="$work/mount"
mkdir "$mount"
hdiutil attach -nobrowse -readonly -noautoopen -mountpoint "$mount" "$dmg" >/dev/null
ok=1
codesign --verify --strict --deep --verbose=2 "$mount/SoundCraft AAF Preview.app" || ok=0
lipo -archs "$mount/SoundCraft AAF Preview.app/Contents/MacOS/SoundCraft"
vtool -arch x86_64 -show-build "$mount/SoundCraft AAF Preview.app/Contents/MacOS/SoundCraft" | grep minos
hdiutil detach "$mount" >/dev/null
[ "$ok" = 1 ] || { echo 'App inside the DMG fails strict verification' >&2; exit 1; }
(cd "$dist_dir" && shasum -a 256 "$(basename "$dmg")" >"$(basename "$dmg").sha256")
echo "Development DMG prepared: $dmg"
echo 'Not a validated RC: Intel hardware, clean-install, listening, long-session, Developer ID and notarization checks remain.'
