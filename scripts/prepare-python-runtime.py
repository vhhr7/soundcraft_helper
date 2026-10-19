"""Fetch a hash-pinned relocatable Python; Python >=3.12 required for data-filter extraction.

Does not install or execute the runtime. Keeps all upstream license material.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def prepare(arch):
    if sys.version_info < (3, 12):
        raise SystemExit('Use Python 3.12+ to safely extract runtime archives')
    lock = json.loads((ROOT / 'packaging/python-runtime.lock.json').read_text())
    spec = lock['architectures'][arch]
    dest = ROOT / 'local-build/runtimes' / lock['release'] / arch
    marker = dest / 'runtime-lock.json'
    if marker.is_file() and json.loads(marker.read_text()) == spec:
        print(dest / 'python')
        return
    if dest.exists():
        raise SystemExit(f'Refusing to replace an existing incomplete runtime: {dest}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='runtime-', dir=dest.parent) as tmp:
        tmp = Path(tmp)
        archive = tmp / 'runtime.tar.gz'
        with urllib.request.urlopen(spec['url'], timeout=60) as response, archive.open('wb') as out:
            shutil.copyfileobj(response, out)
        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if actual != spec['sha256']:
            raise SystemExit(f'Runtime hash mismatch: {actual}')
        extracted = tmp / 'extracted'
        extracted.mkdir()
        with tarfile.open(archive) as tar:
            tar.extractall(extracted, filter='data')
        if not (extracted / 'python/bin/python3').is_file():
            raise SystemExit('Expected a standalone python/bin/python3')
        (extracted / 'runtime-lock.json').write_text(json.dumps(spec, indent=2)+'\n')
        extracted.rename(dest)
    print(dest / 'python')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('architecture', choices=['arm64', 'x86_64'])
    prepare(p.parse_args().architecture)
