"""Run upstream CI on macOS with installed VST3 directories unreadable to the test process.

No plugins are moved or modified. No tests are skipped. Fixture plugins in temporary build
folders still work. This deliberately does not validate compatibility with installed VST3s.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def run(checkout, log, command, timeout):
    if platform.system() != 'Darwin':
        raise SystemExit('This isolation wrapper is for macOS only')
    paths = [Path('/Library/Audio/Plug-Ins/VST3'), Path.home()/'Library/Audio/Plug-Ins/VST3']
    paths.extend(Path(p).absolute() for p in os.environ.get('VST3_PATH','').split(os.pathsep) if p)
    denied = sorted({str(p) for path in paths for p in (path,path.resolve())})
    policy = '(version 1)\n(allow default)\n' + ''.join('(deny file-read* (subpath '+json.dumps(p,ensure_ascii=False)+'))\n' for p in denied)
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('x') as out, tempfile.TemporaryDirectory(prefix='soundcraft-ci-policy-') as tmp:
        profile=Path(tmp)/'vst3.sb';profile.write_text(policy)
        out.write('Isolation: installed VST3 directories unreadable. No test filters/skips.\nCommand: '+json.dumps(command)+'\n');out.flush()
        proc=subprocess.Popen(['/usr/bin/sandbox-exec','-f',str(profile),*command],cwd=checkout,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            code=proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            code=124
        out.write(f'\nExit code: {code}\n')
    print(json.dumps(dict(exit_code=code,log=str(log),system_vst3_access=False,tests_skipped=0)))
    return code

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkout',type=Path,default=ROOT/'local-build/upstream-contribution')
    p.add_argument('--log',type=Path,default=ROOT/'local-tests/upstream-isolated-ci.log')
    p.add_argument('--timeout',type=int,default=900)
    p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args();cmd=a.command
    if cmd[:1]==['--']:cmd=cmd[1:]
    raise SystemExit(run(a.checkout.resolve(),a.log.resolve(),cmd or ['cargo','+1.95.0','xtask','ci'],a.timeout))
