# Draft — import external-WAV AAF as editable session data (pure Rust)

Addresses #40: picture-editor AAF handoffs cannot be opened as editable SoundCraft arrangements.

## What it does

**File → Import → Session Data...** analyzes an AAF, lists its audio tracks and imports the selected ones as new tracks with one clip per edit. Each clip keeps its offset into the complete source, so handles stay available for trimming. Tracks are not consolidated. The import is one undo step, and Save collects the full sources into the session's Audio Files folder.

Supported subset: one CompositionMob whose timeline slots hold SourceClip/Filler sequences, resolved through MasterMobs to SourceMobs with a WAVEDescriptor and one external file locator; mono or interleaved stereo PCM WAV; composition timecode and frame rate, including 24000/1001 and drop-frame. Gain, fades, transitions, selectors, nested sequences, embedded essence, split channels, mixed sample rates and non-local locators fail with an explicit message instead of producing a misleading montage.

## How

- `crates/interchange` (layer 3, no filesystem/process/UI access):
  - `build_session(Plan)`: versioned rational-time plan → `Session`. Endpoints are rounded to samples independently, so adjacent edits share boundaries without drift.
  - `aaf::read_aaf`: reads the AAF object model directly from structured storage through the `cfb` crate (MIT, pure Rust): properties streams, strong reference vectors/sets and dictionary weak references. Media access goes through a `MediaResolver` trait.
- `crates/engine`: `file.preview_aaf` (read-only analysis) and `file.import_aaf` (undoable insertion). Its resolver opens only files named exactly in the media folder the user chose, checks `file_access`, and reads WAV headers without loading sample data. Import re-probes and decodes the media before touching the session.
- `crates/ui-egui`: the Session Data window (track selection, media folder, absolute/relative mapping, sample offset, report).

New dependency: `cfb = "0.15"` (MIT; depends on `uuid`, `fnv`, `web-time`, all already permissive).

## Validation

- Every `cargo xtask ci` step passes on macOS: fmt and clippy in one run; `cargo test --workspace --no-fail-fast` (1162 passed, one upstream benchmark ignored), assets, layers and WASM in a second run after the flaky test below stopped the first. Installed VST3 directories were made unreadable to the test process because a normal run blocked while loading local plugins; no tests were skipped or filtered.
- `random_edits_keep_the_session_sane` can fail on unchanged upstream `25d52c6`: proptest seed `202a144b…` (ops `[(16, 2072628, 0, 2), (7, 859630, 26524, 2), (11, 0, 0, 2)]`) ends with `edit.fades_delete: "Bass: playlist not sorted"`. It reproduces without this patch and is unrelated to AAF; worth its own issue.
- Engine integration tests import a committed synthetic AAF (462 KB, original, two tracks/three edits with chained source offsets) with regenerated WAVs, and check analysis, sample-exact clip positions/offsets, channel layouts and missing/invalid media.
- The reader was developed against an earlier pyaaf2 prototype and produced identical plans for the synthetic fixture, twelve edited variants (relink, frame-based nested offsets, fractional and drop-frame rates, unnamed slots, rejected structures) and a real 22-track, 124-edit AAF with external WAVs. Pro Tools' own import of that file was compared through PTSL: all 124 placed starts/ends/durations, source offsets and handles matched to the sample. The real AAF and its media are not included.

Not verified: long sessions, AAFs from Avid Media Composer/Resolve/Premiere beyond the files above, classroom stability over hours.
