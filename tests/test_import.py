import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import aaf2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from generate_fixture import generate
from soundcraft_aaf.reader import read_aaf, ImportFailure

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / 'target/debug/plan-to-session'


class ImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='soundcraft pruebas ñ ')
        cls.base = Path(cls.tmp.name)
        cls.original = cls.base / 'original'
        generate(cls.original)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.case = self.base / self.id().split('.')[-1]
        shutil.copytree(self.original, self.case)
        self.aaf = self.case / 'Montaje sintético.aaf'

    def change(self, fn):
        with aaf2.open(str(self.aaf), 'rw') as f:
            fn(f, next(f.content.compositionmobs()))

    def test_rational_plan_and_source_chain(self):
        p = read_aaf(self.aaf)
        self.assertEqual([t['name'] for t in p['tracks']], ['01 Diálogo', '02 Ambiente estéreo'])
        self.assertEqual([s['channels'] for s in p['sources']], [1, 2])
        self.assertEqual(p['timecode_start'], [3600, 1])
        self.assertEqual(p['tracks'][0]['clips'][1]['offset'], [7, 2])
        self.assertEqual(p['tracks'][0]['clips'][0]['start'], [1, 1])
        self.assertEqual(p['tracks'][1]['clips'][0]['end'], [5, 1])
        self.assertIn('#', p['sources'][0]['path'])

    def test_explicit_relink_by_filename(self):
        def change(f, c):
            for mob in f.content.sourcemobs():
                locator = mob.descriptor['Locator'].value[0]
                filename = locator['URLString'].value
                locator['URLString'].value = 'file:///missing/old/location/' + filename
        self.change(change)
        with self.assertRaisesRegex(ImportFailure, 'Missing media'):
            read_aaf(self.aaf)
        p = read_aaf(self.aaf, media_dir=self.case)
        self.assertEqual(len(p['sources']), 2)
        self.assertTrue(any(w.startswith('Relinked ') for w in p['warnings']))
        self.assertTrue(all(Path(m['path']).parent == self.case.resolve() for m in p['sources']))
        missing = self.case / 'empty media'
        missing.mkdir()
        with self.assertRaisesRegex(ImportFailure, 'Missing media'):
            read_aaf(self.aaf, media_dir=missing)

    def test_frame_based_file_source_and_nested_offsets(self):
        def change(f, c):
            for m in f.content.mastermobs():
                slot = m.slots[0]
                slot.edit_rate = '24000/1001'
                slot.segment.start = 12
                slot.segment.length = 180
            for m in f.content.sourcemobs():
                m.slots[0].edit_rate = '24000/1001'
                m.slots[0].segment.length = 191
            # These starts address MasterMob frames, while component lengths stay in
            # the composition's 25 fps units and file metadata remains 48000 Hz.
            c.slots[0].segment.components[1].start = 13
            c.slots[0].segment.components[3].start = 60
            c.slots[1].segment.components[0].start = 24
        self.change(change)
        p = read_aaf(self.aaf)
        self.assertEqual(p['sample_rate'], 48000)
        self.assertEqual(p['tracks'][0]['clips'][0]['offset'], [1001, 960])
        self.assertEqual(p['tracks'][1]['clips'][0]['offset'], [3003, 2000])
        # Verify the same normalized plan through the real Rust constructor.
        plan = self.case / 'frame-plan.json'
        plan.write_text(json.dumps(p))
        out = self.case / 'frame-session'
        result = subprocess.run([str(BINARY), str(plan), str(out)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        s = json.loads((out / 'session.scraft').read_text())
        clip = s['tracks'][0]['playlists'][0]['clips'][0]
        self.assertEqual((clip['start'], clip['length'], clip['content']['Audio']['offset']),
                         (48000, 96000, 50050))

    def test_missing_media_explicit(self):
        (self.case / 'Diálogo á #1.wav').unlink()
        with self.assertRaisesRegex(ImportFailure, 'Missing media'):
            read_aaf(self.aaf)

    def test_nonlocal_locator_rejected(self):
        def change(f, c):
            for mob in f.content.sourcemobs():
                mob.descriptor['Locator'].value[0]['URLString'].value = 'https://example.org/media.wav'
        self.change(change)
        with self.assertRaisesRegex(ImportFailure, 'non-local'):
            read_aaf(self.aaf)

    def test_gain_operation_rejected(self):
        def operation(f, c):
            op = f.create.OperationDef('9d2ea890-0968-4839-a5ef-609998f55d1a', 'Synthetic gain')
            op.media_kind = 'sound'
            op.number_inputs = 1
            f.dictionary.register_def(op)
            group = f.create.OperationGroup(op, 50, 'sound')
            seq = c.slots[0].segment
            clip = seq.components.pop(1)
            group.segments.append(clip)
            seq.components.insert(1, group)
        self.change(operation)
        with self.assertRaisesRegex(ImportFailure, 'Unsupported component.*OperationGroup'):
            read_aaf(self.aaf)

    def test_embedded_audio_rejected(self):
        def change(f, c):
            source = next(f.content.sourcemobs())
            source.slots.clear()
            source.import_audio_essence(str(self.case / 'Diálogo á #1.wav'))
        self.change(change)
        with self.assertRaisesRegex(ImportFailure, 'Embedded essence unsupported'):
            read_aaf(self.aaf)

    def test_nonzero_origin_rejected(self):
        self.change(lambda f, c: setattr(c.slots[0], 'origin', 1))
        with self.assertRaisesRegex(ImportFailure, 'origin'):
            read_aaf(self.aaf)

    def test_ambiguous_composition(self):
        def change(f, c):
            f.content.mobs.append(f.create.CompositionMob('alternative'))
        self.change(change)
        with self.assertRaisesRegex(ImportFailure, 'exactly one'):
            read_aaf(self.aaf)

    def test_fractional_rate_is_not_float(self):
        def change(f, c):
            c.slots[0].edit_rate = '24000/1001'
            c.slots[1].edit_rate = '24000/1001'
            c.slots[2].edit_rate = '24000/1001'
            c.slots[2].segment['FPS'].value = 24
        self.change(change)
        p = read_aaf(self.aaf)
        self.assertEqual(p['frame_rate']['rate'], [24000, 1001])
        self.assertEqual(p['tracks'][0]['clips'][0]['start'], [1001, 960])

    def test_end_to_end_session_media_and_failures(self):
        self.assertTrue(BINARY.is_file(), 'Run cargo build --locked before Python tests')
        p = read_aaf(self.aaf)
        plan = self.case / 'plan.json'
        plan.write_text(json.dumps(p), encoding='utf-8')
        out = self.case / 'Sesión con ñ'
        cmd = [str(BINARY), str(plan), str(out)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        s = json.loads((out / 'session.scraft').read_text())
        actual = [(c['start'], c['length'], c['content']['Audio']['offset'])
                  for t in s['tracks'] for c in t['playlists'][0]['clips']]
        self.assertEqual(actual, [(48000, 96000, 48000), (192000, 48000, 168000), (0, 240000, 72000)])
        report = json.loads((out / 'import-report.json').read_text())
        self.assertEqual([(h['before'], h['after']) for h in report['handles']],
                         [(48000, 240000), (168000, 168000), (72000, 72000)])
        for source, original in zip(s['sources'], p['sources']):
            digest = lambda path: hashlib.sha256(Path(path).read_bytes()).digest()
            self.assertEqual(digest(out / source['path']), digest(original['path']))
        self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)  # no overwrite
        p['sources'][0]['frames'] -= 1
        plan.write_text(json.dumps(p))
        bad = self.case / 'bad'
        self.assertNotEqual(subprocess.run([str(BINARY), str(plan), str(bad)], capture_output=True).returncode, 0)
        self.assertFalse(bad.exists())
        p['sources'][0]['frames'] += 1
        Path(p['sources'][0]['path']).unlink()
        plan.write_text(json.dumps(p))
        self.assertNotEqual(subprocess.run([str(BINARY), str(plan), str(bad)], capture_output=True).returncode, 0)
        self.assertFalse(bad.exists())


if __name__ == '__main__':
    unittest.main()
