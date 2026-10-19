"""Generate a self-contained SoundCraft contribution patch without altering the working checkout.

An isolated Git index relocates the exact reusable core into the upstream workspace.
No commit, branch, push or PR is created. The optional reader remains a separate integration choice.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / 'upstream'
BASE = '25d52c646aea780c8076ff966076f994ad256221'

def export(checkout=None):
    def git(*args, data=None, env=None):
        return subprocess.check_output(['git', '-C', str(UPSTREAM), *args], input=data, env=env)
    if git('rev-parse', 'HEAD').decode().strip() != BASE:
        raise SystemExit('Upstream base changed; review and regenerate the development overlay first')
    patch = ROOT / 'integration/soundcraft-aaf.patch'
    if patch.read_bytes() != git('diff', '--binary'):
        raise SystemExit('Development overlay differs from the working source; review it before exporting')
    with tempfile.TemporaryDirectory(prefix='soundcraft-export-') as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp)/'index'))
        git('read-tree', BASE, env=env)
        git('apply', '--cached', str(patch), env=env)
        def read(path):
            return git('show', ':'+path, env=env).decode()
        def put(path, content):
            blob = git('hash-object', '-w', '--stdin', data=content.encode(), env=env).decode().strip()
            git('update-index', '--add', '--cacheinfo', '100644', blob, path, env=env)
        core = subprocess.check_output([os.environ.get('SOUNDCRAFT_RUSTFMT', 'rustfmt'), '+1.95.0', '--edition', '2024', '--config-path', str(UPSTREAM), '--emit', 'stdout'], input=(ROOT/'src/lib.rs').read_bytes()).decode()
        put('crates/interchange/src/lib.rs', core)
        put('crates/interchange/Cargo.toml', '''[package]
name = "soundcraft-interchange"
description = "Rational-time interchange plans and editable session construction"
version.workspace = true
edition.workspace = true
license = "MIT"
rust-version.workspace = true
repository.workspace = true

[dependencies]
soundcraft-model.workspace = true
soundcraft-time.workspace = true
soundcraft-audio-io.workspace = true
serde.workspace = true
serde_json.workspace = true
thiserror.workspace = true

[lints]
workspace = true
''')
        put('crates/interchange/README.md', '''# Interchange core

Pure Rust Plan → Session constructor, originally developed in vhhr7/soundcraft_helper.
No format parser, process, UI or filesystem access. Rational endpoints are converted to
samples independently; sources retain complete media bounds and clips retain source offsets.

The AAF engine adapter accepts a configured optional external reader through
SOUNDCRAFT_AAF_PYTHON and SOUNDCRAFT_AAF_READER. Reader packaging and upstream's
pure-Rust policy require review; this patch is not a complete bundled AAF release.
The desktop preview returns an explicit error when the reader is unavailable.
''')
        put('Cargo.toml', read('Cargo.toml').replace('# internal\n', '# internal\nsoundcraft-interchange = { path = "crates/interchange" }\n', 1))
        put('crates/engine/Cargo.toml', read('crates/engine/Cargo.toml').replace('soundcraft-interchange = { path = "../../.." }', 'soundcraft-interchange.workspace = true'))
        put('Cargo.lock', read('Cargo.lock').replace('name = "soundcraft-interchange"\nversion = "0.1.0"', 'name = "soundcraft-interchange"\nversion = "0.9.0"'))
        put('xtask/src/main.rs', read('xtask/src/main.rs').replace('    ("mix", 3),', '    ("mix", 3),\n    ("interchange", 3),', 1))
        credit = json.loads((ROOT/'integration/contributor.json').read_text())
        if credit['github_username'] != 'vhhr7':
            raise SystemExit('This consent applies only to the helper contributor vhhr7')
        people = read('contributors/people.toml')
        if '[people.vhhr7]' in people:
            raise SystemExit('An upstream entry already exists; reconcile it with the contributor before changing it')
        put('contributors/people.toml', people.rstrip()+'\n\n# Display name explicitly chosen by the contributor on 2026-10-19.\n[people.vhhr7]\ndisplay_name = '+json.dumps(credit['display_name'], ensure_ascii=False)+'\n')

        result = git('diff', '--cached', '--binary', BASE, env=env)
        output = ROOT/'integration/upstream-aaf.patch'
        output.write_bytes(result)
        if checkout:
            checkout = Path(checkout).resolve()
            if checkout.exists():
                raise SystemExit(f'Refusing to overwrite {checkout}')
            subprocess.run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(UPSTREAM), str(checkout)], check=True)
            subprocess.run(['git', '-C', str(checkout), 'checkout', '--quiet', '--detach', BASE], check=True)
            subprocess.run(['git', '-C', str(checkout), 'apply', str(output)], check=True)
        files = git('diff', '--cached', '--name-only', BASE, env=env).decode().splitlines()
    (ROOT/'integration/upstream-export.json').write_text(json.dumps(dict(base=BASE,sha256=hashlib.sha256(result).hexdigest(),files=files,ci='pending; run in independent checkout',reader_packaging='optional runtime requires maintainer review'),indent=2)+'\n')
    print(output)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkout', help='Optional new directory to materialize for independent tests')
    export(p.parse_args().checkout)
