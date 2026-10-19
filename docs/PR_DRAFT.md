# Draft — add reusable AAF interchange session builder and strict external-WAV prototype

Picture-editor AAF handoffs cannot currently be opened as editable SoundCraft arrangements (#40). This first-stage prototype builds SoundCraft sessions from a versioned rational-time interchange plan and exercises that same Rust library through a small CLI. A separate MIT-licensed pyaaf2 adapter reads a deliberately restricted AAF subset; it never constructs SoundCraft's session JSON.

The prototype preserves ordered/named audio tracks, individual SourceClip edits, gaps, source-chain offsets, full referenced WAV media and available handles, mono/interleaved stereo, and direct composition timecode/frame rate. It rounds absolute endpoints into samples to prevent accumulated edit-rate drift. Missing media, ambiguous compositions, unsupported editorial structures and source windows outside the available audio fail explicitly. It does not consolidate tracks.

Scope for this review: helper repository and reusable module, not a completed SoundCraft menu integration. Upstream model is pinned at 25d52c646aea780c8076ff966076f994ad256221. SoundCraft upstream has no code changes in this checkout. The future upstream patch should move the constructor to a layered crate, use engine file-access policies, and expose a command only after reader packaging is resolved. The Python reader is a practical prototype choice; it is not presumed acceptable under the pure-Rust project policy.

Validation performed:

- Rust unit tests for sample positions/durations/offsets/handles, model JSON roundtrip, stereo/names/order, invalid metadata/windows, overflow, and fractional-frame boundaries including 44.1 kHz.
- Python binary AAF tests including external Unicode/space/# paths, gaps, nested source offsets, composition selection, missing media, nonlocal locators, nonzero origins, embedded essence rejection and gain OperationGroup rejection.
- End-to-end CLI test checks sample values and full-source byte identity, refusal to overwrite, missing media and independent WAV metadata verification.
- Native SoundCraft 0.8.0, launched without audio: session inspection, loaded media, clip extension at both edges, save-copy and reopen. Screenshot inspected. Transcript and script included.
- `cargo fmt --check`, `cargo clippy --locked --all-targets -- -D warnings`, `cargo test --locked`, Python unittest suite. Full upstream `cargo xtask ci` was not run; unchanged upstream GUI was not built.

Not supported: OMF, embedded-media extraction, split stereo/channel selection, mixed sample rates/resampling, MXF/AIFF, gain/fades/transitions/effects, selectors, nested editorial sequences, timewarp, arbitrary slot origins, plugins, routing or automation. Non-audio slots and unsupported metadata are reported as outside scope. Producer-specific clip naming and gain/fade encodings need real-world fixtures; no interchange equivalence is claimed.

A real external-media AAF (22 tracks, 124 clips/sources) was also imported and inspected in SoundCraft after explicit filename relink; source slot edit rates are distinct from audio sample rates. All clip coordinates survived native save-copy/reopen. No independent Pro Tools comparison, audible playback check, full current-version UI build, long-session testing or classroom stability certification has been completed. This is a tested base for further work and must not close the whole interchange gap.

Before a future upstream PR: re-check open work and craftrules, obtain the contributor's preferred optional credit once, run upstream gates, and update attribution/progress documentation. No PR has been published and no maintainer has been contacted.
