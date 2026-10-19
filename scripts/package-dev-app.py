"""Package an isolated development app; never touches /Applications/SoundCraft.app."""
import os
from pathlib import Path
import plistlib
import shutil

root=Path(__file__).resolve().parents[1]
app=root/'local-build/SoundCraft AAF Preview.app'
contents=app/'Contents'
macos=contents/'MacOS'
macos.mkdir(parents=True,exist_ok=True)
binary=root/'local-build/target/debug/soundcraft'
staged=macos/'SoundCraft-bin.new'
shutil.copy2(binary,staged)
os.replace(staged,macos/'SoundCraft-bin')
# Shell escaping for the project's location, including spaces and shell metacharacters.
import shlex
launcher='''#!/bin/sh
set -eu
project_dir=PROJECT
export SOUNDCRAFT_AAF_PYTHON="$project_dir/.venv/bin/python"
export SOUNDCRAFT_AAF_READER="$project_dir/scripts/aaf_bridge.py"
export SOUNDCRAFT_CONFIG_DIR="$project_dir/local-build/profile"
app_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$app_dir/SoundCraft-bin" --control "${SOUNDCRAFT_DEV_CONTROL_PORT:-0}" "$@"
'''.replace('PROJECT',shlex.quote(str(root)))
(macos/'SoundCraftAAF').write_text(launcher)
(macos/'SoundCraftAAF').chmod(0o755)
plist=dict(CFBundleName='SoundCraft AAF Preview',CFBundleDisplayName='SoundCraft AAF Preview',CFBundleIdentifier='net.vicherrera.soundcraft.aaf-preview',CFBundleExecutable='SoundCraftAAF',CFBundlePackageType='APPL',CFBundleShortVersionString='0.9.0',CFBundleVersion='1',NSHighResolutionCapable=True,NSMicrophoneUsageDescription='Record audio when explicitly armed in SoundCraft.',LSMinimumSystemVersion='11.0')
with (contents/'Info.plist').open('wb') as f:plistlib.dump(plist,f)
print(app)
