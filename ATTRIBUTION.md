# Attribution

| Path | Author/source | License |
|---|---|---|
| `demo/AAF con espacios ñ/*.wav` | Original PCM synthesized by `scripts/generate_fixture.py`, soundcraft_helper contributors | MIT, LICENSE |
| `demo/AAF con espacios ñ/*.aaf` | Original synthetic composition generated with pyaaf2; no proprietary content | MIT, LICENSE |
| `demo/Sesión SoundCraft/Audio Files/*.wav` | Byte-identical copies of original synthesized sources | MIT, LICENSE |
| `docs/app-validation/*.png` | Local screenshots of SoundCraft displaying only the synthetic demo; SoundCraft UI by ArtCraft contributors | SoundCraft MIT OR Apache-2.0; see upstream notices |
| `upstream/` | ArtCraft Team and SoundCraft contributors, pinned git submodule | MIT OR Apache-2.0; licenses and NOTICE in submodule |
| runtime dependency `pyaaf2==1.7.1` | Mark Reid, https://github.com/markreidvfx/pyaaf2 | MIT; hash-pinned wheel included only in generated portable apps, with its license |

Rust transitive crates are recorded in Cargo.lock and retain their respective notices. No LibAAF, Omfoo, AAF SDK, Pro Tools assets or proprietary audio is bundled.

Generated portable builds include hash-pinned CPython distributions from https://github.com/astral-sh/python-build-standalone (release 20261013; Python 3.13.16). The complete distribution license material, including bundled dependency notices, remains in each runtime; runtime binaries are generated/downloaded under ignored local-build and local-tests directories, not committed. packaging/python-runtime.lock.json records provenance and hashes. The native preview launcher and packaging scripts are original MIT code from this repository.
