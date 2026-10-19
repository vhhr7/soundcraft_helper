"""Original synthesized PCM and AAF. No proprietary material. MIT, project contributors."""
import argparse
from pathlib import Path
import math
import struct
import wave
from urllib.parse import quote
import aaf2
from aaf2.ama import get_wave_fmt, create_network_locator


def generate(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    paths = []
    for ch, title in [(1, 'Diálogo á #1'), (2, 'Ambiente estéreo')]:
        path = folder / f'{title}.wav'
        with wave.open(str(path), 'wb') as w:
            w.setparams((ch, 2, 48000, 0, 'NONE', 'not compressed'))
            # 8 s full sources, quiet tones + impulse each second make alignment audible.
            data = bytearray()
            for i in range(48000 * 8):
                for c in range(ch):
                    tone = .06 * math.sin(2 * math.pi * (220 + 110*c) * i / 48000)
                    impulse = .4 if i % 48000 < 48 else 0
                    data.extend(struct.pack('<h', int((tone+impulse)*32767)))
            w.writeframes(data)
        paths.append(path)
    aaf = folder / 'Montaje sintético.aaf'
    with aaf2.open(str(aaf), 'w') as f:
        comp = f.create.CompositionMob('Clase AAF — cortes y handles')
        f.content.mobs.append(comp)
        for index, path in enumerate(paths):
            source = f.create.SourceMob(path.stem)
            f.content.mobs.append(source)
            file_slot = source.create_empty_slot(48000, 'sound')
            file_slot.segment.length = 384000
            desc = f.create.WAVEDescriptor()
            desc['SampleRate'].value = 48000
            desc['Length'].value = 384000
            desc['Summary'].value = get_wave_fmt(str(path))
            desc['ContainerFormat'].value = f.dictionary.lookup_containerdef('AAF')
            locator = f.create.NetworkLocator()
            locator['URLString'].value = quote(path.name)
            desc['Locator'].append(locator)
            source.descriptor = desc
            master = f.create.MasterMob(path.stem)
            f.content.mobs.append(master)
            ms = master.create_timeline_slot(48000)
            # Additional 0.5 s in master chain: verifies source-chain offsets.
            ms.segment = source.create_source_clip(file_slot.slot_id, start=24000, length=360000)
            ts = comp.create_sound_slot(25)
            ts.name = ('01 Diálogo', '02 Ambiente estéreo')[index]
            if index == 0:
                ts.segment.components.append(f.create.Filler('sound', 25))
                ts.segment.components.append(master.create_source_clip(ms.slot_id, start=24000, length=50))
                ts.segment.components.append(f.create.Filler('sound', 25))
                ts.segment.components.append(master.create_source_clip(ms.slot_id, start=144000, length=25))
            else:
                ts.segment.components.append(master.create_source_clip(ms.slot_id, start=48000, length=125))
            ts.segment.length = sum(c.length for c in ts.segment.components)
        tc = comp.create_timeline_slot(25)
        tc.segment = f.create.Timecode(25, drop=False, length=125)
        tc.segment['Start'].value = 90000  # 01:00:00:00 at 25 fps
    return aaf


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('folder')
    print(generate(p.parse_args().folder))
