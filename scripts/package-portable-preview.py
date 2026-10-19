"""Assemble a relocatable preview app from explicit binaries and pinned bundled runtimes.

A development package, not a validated RC. Refuses existing destinations. Does not download,
install into Applications, remove quarantine, sign with a real identity, or publish anything.
"""
import argparse
import hashlib
import json
import plistlib
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.9.0-aaf.1-dev.2'

def archs(path):
    return set(subprocess.check_output(['lipo','-archs',str(path)],text=True).split())

def package(binary, launcher, output, architectures):
    for name,path in [('SoundCraft',binary),('launcher',launcher)]:
        if not architectures.issubset(archs(path)):
            raise SystemExit(f'{name} does not contain all requested architectures')
    lock = json.loads((ROOT/'packaging/python-runtime.lock.json').read_text())
    runtimes={a:ROOT/'local-build/runtimes'/lock['release']/a/'python' for a in architectures}
    for a,p in runtimes.items():
        if not p.is_dir() or archs(p/'bin/python3') != {a}:
            raise SystemExit(f'Prepare the pinned {a} runtime first')
        if json.loads((p.parent/'runtime-lock.json').read_text()) != lock['architectures'][a]:
            raise SystemExit(f'Runtime lock mismatch: {a}')
    wheels=list((ROOT/'local-build/downloads').glob('pyaaf2-1.7.1-*.whl'))
    if len(wheels)!=1:
        raise SystemExit('Download exactly one hash-verified pyaaf2 1.7.1 wheel first')
    wheel=wheels[0]
    digest=hashlib.sha256(wheel.read_bytes()).hexdigest()
    if digest not in (ROOT/'requirements.txt').read_text():
        raise SystemExit('pyaaf2 wheel hash is not in requirements.txt')
    if output.exists():
        raise SystemExit(f'Refusing to overwrite {output}')
    macos=output/'Contents/MacOS';resources=output/'Contents/Resources'
    macos.mkdir(parents=True);resources.mkdir()
    shutil.copy2(binary,macos/'SoundCraft-bin')
    shutil.copy2(launcher,macos/'SoundCraftAAF')
    for a,p in runtimes.items():
        shutil.copytree(p,resources/'Python'/a/'python',symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    aaf=resources/'aaf';(aaf/'scripts').mkdir(parents=True)
    shutil.copy2(ROOT/'scripts/aaf_bridge.py',aaf/'scripts/aaf_bridge.py')
    shutil.copytree(ROOT/'python',aaf/'python',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    with zipfile.ZipFile(wheel) as z:
        for n in z.namelist():
            if Path(n).is_absolute() or '..' in Path(n).parts:
                raise SystemExit('Invalid wheel archive path')
        z.extractall(aaf/'deps')
    notices=resources/'Notices';notices.mkdir()
    for name in ['LICENSE-MIT','LICENSE-APACHE','NOTICE','ATTRIBUTION.md']:
        p=ROOT/'upstream'/name
        if p.is_file():shutil.copy2(p,notices/('SoundCraft-'+name))
    for name in ['LICENSE','requirements.txt']:
        shutil.copy2(ROOT/name,notices/name)
    (notices/'README.txt').write_text('Unofficial development preview based on SoundCraft by its upstream contributors.\nAAF integration developed in vhhr7/soundcraft_helper.\nPython distribution licenses are retained inside Resources/Python.\npyaaf2 MIT license is retained in Resources/aaf/deps/pyaaf2-1.7.1.dist-info.\nNo ArtCraft brand artwork is included. No classroom or Intel validation is implied.\n')
    info=dict(CFBundleName='SoundCraft AAF Preview',CFBundleDisplayName='SoundCraft AAF Preview',CFBundleIdentifier='net.vicherrera.soundcraft.aaf-preview.portable',CFBundleExecutable='SoundCraftAAF',CFBundlePackageType='APPL',CFBundleShortVersionString='0.9.0',CFBundleVersion='3',NSHighResolutionCapable=True,NSMicrophoneUsageDescription='Record audio when explicitly armed.',LSMinimumSystemVersion='11.0')
    with (output/'Contents/Info.plist').open('wb') as f:plistlib.dump(info,f)
    manifest=dict(version=VERSION,stage='development; not an RC',architectures=sorted(architectures),upstream_base='25d52c646aea780c8076ff966076f994ad256221',binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),launcher_sha256=hashlib.sha256(launcher.read_bytes()).hexdigest(),runtime=lock,pyaaf2_sha256=digest,developer_id_signed=False,notarized=False,minimum_macos='11.0 requested; not yet validated',intel_hardware_test='pending',classroom_test='pending')
    (resources/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(output)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--launcher',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--architectures',nargs='+',choices=['arm64','x86_64'],required=True)
    a=p.parse_args()
    package(a.binary.resolve(),a.launcher.resolve(),a.output.resolve(),set(a.architectures))
