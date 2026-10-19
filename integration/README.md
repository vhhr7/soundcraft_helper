# Native AAF development overlay

Base: `25d52c646aea780c8076ff966076f994ad256221` (SoundCraft 0.9.0).
Apply: `../scripts/apply-ui-overlay.sh` from any directory.
Build and run: see `../docs/graphical-import.md`.

The patch is deliberately tracked in the helper repository while the upstream submodule stays pinned to a published base. It reuses this repository's Rust session builder and Python reader. No proprietary assets or user AAF/media are included. Do not submit this overlay unchanged upstream: first relocate the reusable core into the upstream workspace and agree on optional reader packaging.

## Self-contained contribution export

`scripts/export-upstream.py` generates `upstream-aaf.patch` and `upstream-export.json` without changing the development checkout. It relocates the same core into `crates/interchange`, registers layer 3 and removes the helper path dependency. The Python reader remains optional runtime configuration and still requires upstream policy/packaging review.

`python3 scripts/export-upstream.py --checkout local-build/upstream-contribution` also creates an independent local Git checkout for tests. Existing destinations are refused. No commits, push or PR are made. See `docs/rc-and-upstream.md` for current gates and limitations.
