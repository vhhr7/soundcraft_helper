"""Strict, non-destructive AAF reader emitting interchange schema v1.

No SoundCraft JSON is constructed here. All times are rational seconds, not floats.
Unsupported editorial structures abort rather than produce a misleading montage.
"""
from fractions import Fraction
from pathlib import Path
from urllib.parse import urlsplit, unquote
import wave
import aaf2
from aaf2 import components, mobs, mobslots, essence

MAX_ITEMS = 100_000
MAX_AAF_BYTES = 512 * 1024 * 1024


class ImportFailure(ValueError):
    pass


def rational(value):
    f = Fraction(value)
    return [f.numerator, f.denominator]


def rate(slot):
    if not isinstance(slot, mobslots.TimelineMobSlot) or slot.origin != 0:
        raise ImportFailure(f"Unsupported slot/origin: {slot}")
    r = Fraction(slot.edit_rate)
    if r <= 0:
        raise ImportFailure("Edit rate must be positive")
    return r


def locator_path(url, base):
    u = urlsplit(url)
    if u.scheme not in ("", "file") or u.netloc not in ("", "localhost"):
        raise ImportFailure(f"Unsupported non-local locator: {url}")
    if u.query or u.fragment:
        raise ImportFailure(f"Locator must escape special characters: {url}")
    p = Path(unquote(u.path))
    return (p if p.is_absolute() else base / p).resolve()


def read_aaf(path, composition=None):
    path = Path(path).resolve()
    if not path.is_file() or path.stat().st_size > MAX_AAF_BYTES:
        raise ImportFailure("AAF missing, not a regular file, or above 512 MiB")
    with aaf2.open(str(path), "r") as f:
        comps = list(f.content.compositionmobs())
        if composition is not None:
            comps = [m for m in comps if str(m.mob_id) == composition]
        if len(comps) != 1:
            raise ImportFailure("Choose exactly one composition by MobID: " +
                                repr([(m.name, str(m.mob_id)) for m in comps]))
        comp = comps[0]
        plan = dict(schema_version=1, name=comp.name or path.stem,
                    sample_rate=0, timecode_start=[0, 1], frame_rate=None,
                    sources=[], tracks=[], warnings=[
                        "AAF subset: plugins, routing, automation and metadata are not transferred.",
                        "Clip gain, fades, transitions, selectors, nested sequences and embedded media are unsupported; encountered editorial structures fail."])
        sources = {}
        count = 0

        def resolve(ref, incoming_rate, offset=Fraction(0), seen=()):
            if not isinstance(ref, components.SourceClip):
                raise ImportFailure(f"Unsupported source chain component: {type(ref).__name__}")
            mob, slot = ref.mob, ref.slot
            if mob is None or slot is None:
                raise ImportFailure(f"Unresolved SourceClip MobID/slot: {ref.mob_id}/{ref.slot_id}")
            key = (str(mob.mob_id), slot.slot_id)
            if key in seen or len(seen) >= 32:
                raise ImportFailure("Cyclic or too deep source chain")
            rr = rate(slot)
            offset += Fraction(ref.start) / rr
            if isinstance(mob, mobs.SourceMob) and any(str(e.mob_id) == str(mob.mob_id) for e in f.content.essencedata):
                raise ImportFailure(f"Embedded essence unsupported: {mob.name}")
            # A file source terminates the logical chain; its physical/tape reference is not an offset.
            if isinstance(mob, mobs.SourceMob) and isinstance(mob.descriptor, essence.WAVEDescriptor):
                desc = mob.descriptor
                locs = [l['URLString'].value for l in desc['Locator'].value]
                if len(locs) != 1:
                    raise ImportFailure(f"Expected one unambiguous WAV locator: {mob.name}")
                source_path = locator_path(locs[0], path.parent)
                if not source_path.is_file():
                    raise ImportFailure(f"Missing media: {source_path}; locator={locs[0]}")
                with wave.open(str(source_path), 'rb') as w:
                    sr, channels, frames = w.getframerate(), w.getnchannels(), w.getnframes()
                    if channels not in (1, 2) or w.getcomptype() != 'NONE':
                        raise ImportFailure("Only mono/stereo PCM WAV supported")
                if Fraction(desc['SampleRate'].value) != sr or rr != sr:
                    raise ImportFailure(f"Descriptor/file/edit sample rates differ: {mob.name}")
                if desc['Length'].value != frames:
                    raise ImportFailure(f"Descriptor/file lengths differ: {mob.name}")
                # Full interleaved WAV only: a selected physical channel needs a channel map
                # that SoundCraft ClipContent does not currently expose.
                physical = slot['PhysicalTrackNumber'].value if 'PhysicalTrackNumber' in slot else None
                if physical not in (None, 0):
                    raise ImportFailure("Physical channel selection / split stereo unsupported")
                sid = str(mob.mob_id)
                if sid not in sources:
                    sources[sid] = dict(key=sid, name=mob.name or source_path.stem,
                                        path=str(source_path), channels=channels,
                                        frames=frames, sample_rate=sr)
                return sid, offset
            if not isinstance(mob, mobs.MasterMob):
                raise ImportFailure(f"Unsupported referenced mob/descriptor: {mob}")
            if offset < 0 or offset + Fraction(ref.length) / incoming_rate > Fraction(slot.length) / rr:
                raise ImportFailure(f"SourceClip exceeds master slot: {mob.name}")
            if not isinstance(slot.segment, components.SourceClip):
                raise ImportFailure(f"Unsupported master segment: {type(slot.segment).__name__}")
            return resolve(slot.segment, rr, offset, seen + (key,))

        tc_seen = False
        for slot in comp.slots:
            if len(plan['tracks']) >= MAX_ITEMS:
                raise ImportFailure("Too many tracks")
            rr = rate(slot)
            seg = slot.segment
            if isinstance(seg, components.Timecode):
                if tc_seen:
                    raise ImportFailure("Multiple timecode slots unsupported")
                tc_seen = True
                fps = seg['FPS'].value
                drop = seg['Drop'].value
                if round(rr) != fps:
                    raise ImportFailure("Timecode FPS disagrees with edit rate")
                plan['frame_rate'] = dict(rate=rational(rr), drop=bool(drop))
                plan['timecode_start'] = rational(Fraction(seg['Start'].value) / rr)
                continue
            if slot.media_kind != 'Sound':
                plan['warnings'].append(f"Skipped non-audio slot {slot.slot_id}: {slot.media_kind}")
                continue
            track = dict(name=slot.name or f"Audio {slot.slot_id}", channels=1, clips=[])
            items = list(seg.components) if isinstance(seg, components.Sequence) else [seg]
            cursor = 0
            formats = set()
            for item in items:
                count += 1
                if count > MAX_ITEMS:
                    raise ImportFailure("Too many components")
                if item.length < 0:
                    raise ImportFailure("Negative component length")
                if isinstance(item, components.Filler):
                    cursor += item.length
                    continue
                if not isinstance(item, components.SourceClip):
                    raise ImportFailure(f"Unsupported component in {track['name']}: {type(item).__name__}")
                sid, offset = resolve(item, rr)
                formats.add(sources[sid]['channels'])
                track['clips'].append(dict(name=item.mob.name or sources[sid]['name'], source=sid,
                    start=rational(Fraction(cursor) / rr),
                    end=rational(Fraction(cursor + item.length) / rr), offset=rational(offset)))
                cursor += item.length
            if isinstance(seg, components.Sequence) and seg.length != cursor:
                raise ImportFailure("Sequence declared length differs from components")
            if len(formats) > 1:
                raise ImportFailure(f"Mixed channel layouts in track: {track['name']}")
            if formats:
                track['channels'] = formats.pop()
            else:
                plan['warnings'].append(f"Empty track {track['name']}: mono layout assumed")
            plan['tracks'].append(track)
        plan['sources'] = list(sources.values())
        rates = {s['sample_rate'] for s in sources.values()}
        if len(rates) != 1:
            raise ImportFailure("Require at least one source and a single source sample rate; no resampling yet")
        plan['sample_rate'] = rates.pop()
        if not tc_seen:
            plan['warnings'].append("No composition timecode: start=0, frame rate defaults to 30")
        return plan
