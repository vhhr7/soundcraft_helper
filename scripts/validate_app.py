"""Validate a dedicated SoundCraft instance via its documented local control API.
Start a dedicated instance with --control PORT (optionally --no-audio); never use user projects.
Uses a new output directory. Does not play, record, scan plugins or alter preferences.
"""
import argparse
import json
from pathlib import Path
import socket


def validate(port, output, screenshots=True):
    output = Path(output).resolve()
    output.mkdir(exist_ok=False)
    transcript = []
    with socket.create_connection(('127.0.0.1', port), timeout=15) as sock:
        stream = sock.makefile('rwb')
        def rpc(method, params):
            req = dict(id=len(transcript)+1, method=method, params=params)
            stream.write((json.dumps(req)+'\n').encode()); stream.flush()
            result = json.loads(stream.readline())
            transcript.append(dict(request=req, response=result))
            (output / 'transcript.json').write_text(json.dumps(transcript, ensure_ascii=False, indent=2))
            if not result.get('ok'):
                raise RuntimeError(result)
            return result['result']
        def command(name, **params):
            return rpc('engine.execute', dict(command=name, params=params))
        def inspect():
            return rpc('session.inspect', dict(detail='full'))
        def signature(session):
            return [(c['start'], c['length'], c['offset']) for t in session['tracks'] for c in t['clips']]
        initial = inspect()
        if initial['name'] != 'Clase AAF — cortes y handles':
            raise RuntimeError('Refusing to modify a session other than the synthetic demo')
        expected = [(48000,96000,48000),(192000,48000,168000),(0,240000,72000)]
        assert signature(initial) == expected
        assert [t['name'] for t in initial['tracks']] == ['01 Diálogo','02 Ambiente estéreo']
        assert [t['format'] for t in initial['tracks']] == ['Mono','Stereo']
        assert all(s['loaded'] and s['frames']==384000 for s in initial['sources'])
        assert initial['sample_rate']==48000 and initial['frame_rate']=='25'
        command('view.zoom_fit', width_px=1600)
        if screenshots:
            rpc('ui.screenshot', dict(path=str(output / 'montage.png')))
        clip = initial['tracks'][0]['clips'][0]['id']
        command('edit.trim_clip', clip=clip, start=24000, end=168000)
        extended = inspect()
        assert signature(extended)[0] == (24000,144000,24000), signature(extended)
        # Restore original edit explicitly, then save a separate native copy and reopen it.
        command('edit.trim_clip', clip=clip, start=48000, end=144000)
        copy = output / 'roundtrip' / 'roundtrip.scraft'
        command('session.save_copy', path=str(copy))
        opened = command('session.open', path=str(copy))
        assert not opened.get('missing'), opened
        reopened = inspect()
        saved = json.loads(copy.read_text())
        assert saved['timecode_start'] == 172800000 and saved['frame_rate'] == 'Fps25'
        assert signature(reopened) == expected
        assert all(s['loaded'] for s in reopened['sources'])
        if screenshots:
            rpc('ui.screenshot', dict(path=str(output / 'reopened.png')))
        audio = rpc('ui.inspect', {})
        summary = dict(validated=True, tracks=2, clips=3, media_loaded=2,
                       trim_both_handles=True, save_copy_reopen=True,
                       playback_verified=False, audio_device_reported=audio.get('audio_device'),
                       screenshots_requested=screenshots)
        (output / 'summary.json').write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--port',type=int,required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--skip-screenshots', action='store_true', help='Validate model/media without requiring a visible GPU frame')
    a=p.parse_args()
    validate(a.port,a.output,not a.skip_screenshots)
