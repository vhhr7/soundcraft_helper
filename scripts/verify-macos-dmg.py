"""Verify a generated universal DMG and its extracted app; no system installation or publication."""
import argparse
import json
from pathlib import Path
import platform
import plistlib
import subprocess


def verify(dmg, output):
    output.mkdir(parents=True, exist_ok=False)
    mount=output/'mount';mount.mkdir()
    report=dict(dmg=str(dmg),container_valid=False,signature='ad-hoc; no Developer ID/notarization',physical_intel_test=False)
    def run(*cmd):
        try:return subprocess.check_output(list(map(str,cmd)),stderr=subprocess.STDOUT,text=True)
        except subprocess.CalledProcessError as e:raise RuntimeError(f'{cmd[0]} failed: {e.output}') from e
    run('hdiutil','verify',dmg);report['container_valid']=True
    attached=False
    try:
        run('hdiutil','attach','-readonly','-nobrowse','-noautoopen','-mountpoint',mount,dmg);attached=True
        apps=list(mount.glob('*.app'))
        if len(apps)!=1:raise RuntimeError('Expected exactly one app in DMG')
        original=apps[0]
        run('codesign','--verify','--strict','--deep',original)
        app=output/'installed'/original.name;app.parent.mkdir()
        run('ditto',original,app)
        run('codesign','--verify','--strict','--deep',app)
        report['mounted_app_signature_valid']=True;report['extracted_app_signature_valid']=True
        with (app/'Contents/Info.plist').open('rb') as f:info=plistlib.load(f)
        report['bundle_id']=info['CFBundleIdentifier'];report['minimum_macos_declared']=info['LSMinimumSystemVersion']
        macos=app/'Contents/MacOS'
        report['architectures']={}
        for name in ['SoundCraft-bin','SoundCraftAAF']:
            archs=set(run('lipo','-archs',macos/name).split())
            if archs!={'arm64','x86_64'}:raise RuntimeError(f'{name}: not universal')
            report['architectures'][name]=sorted(archs)
        # Check all bundled Mach-O dependencies for developer-machine absolute paths.
        magics={b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca',b'\xca\xfe\xba\xbf'}
        seen=set();external=[]
        for p in app.rglob('*'):
            if not p.is_file():continue
            real=p.resolve()
            if real in seen:continue
            seen.add(real)
            with p.open('rb') as f:magic=f.read(4)
            if magic not in magics:continue
            # otool -L lists the image's LC_ID_DYLIB as well as actual load dependencies.
            install_ids={line.strip() for line in run('otool','-D',p).splitlines() if line.strip() and not line.rstrip().endswith(':')}
            for line in run('otool','-L',p).splitlines():
                if not line.startswith('\t'):continue
                dep=line.strip().split(' (',1)[0]
                if dep in install_ids:continue
                if not dep.startswith(('@rpath/','@loader_path/','@executable_path/','/usr/lib/','/System/Library/')):
                    external.append(dict(binary=str(p.relative_to(app)),dependency=dep))
        if external:raise RuntimeError('External dynamic dependencies: '+json.dumps(external))
        report['external_dynamic_dependencies']=[]
        report['self_tests']={}
        arches=['x86_64'] if platform.machine()=='x86_64' else ['arm64','x86_64']
        for arch in arches:
            version=run('/usr/bin/arch','-'+arch,macos/'SoundCraft-bin','--version').strip()
            reader=json.loads(run('/usr/bin/arch','-'+arch,macos/'SoundCraftAAF','--reader-self-test'))
            report['self_tests'][arch]=dict(engine_version=version,reader=reader,mode='native' if arch==platform.machine() else 'Rosetta; not physical Intel')
        run('codesign','--verify','--strict','--deep',app)
        report['signature_after_runtime_self_tests']=True
        report['app']=str(app)
    finally:
        if attached:run('hdiutil','detach',mount)
        (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dmg',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();verify(a.dmg.resolve(),a.output.resolve())
