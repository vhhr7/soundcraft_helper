"""Trusted subprocess adapter for the development SoundCraft build.

Run with the project's Python interpreter and -I. No session construction here.
"""
import argparse
import json
from pathlib import Path
import sys

base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base / 'python'))
sys.path.insert(0, str(base / 'deps'))
from soundcraft_aaf.reader import read_aaf

if sys.argv[1:] == ['--self-test']:
    import aaf2
    print(json.dumps(dict(reader='pyaaf2', version=aaf2.__version__, python=sys.version.split()[0])))
    sys.exit(0)

p = argparse.ArgumentParser()
p.add_argument('aaf')
p.add_argument('--media-dir', required=True)
p.add_argument('--composition')
a = p.parse_args()
try:
    result = read_aaf(a.aaf, a.composition, a.media_dir)
    print(json.dumps(result, ensure_ascii=False))
except Exception as e:
    print(f'{type(e).__name__}: {e}', file=sys.stderr)
    sys.exit(1)
