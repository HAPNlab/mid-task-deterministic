# Release Guide

This document describes how releases of `mid-task-deterministic` are versioned,
verified, and published.

Because this task is used to collect real fMRI data, **a stable release is a promise
that timing and measurements have been verified on production hardware**. Anything not
fully verified is published only as a pre-release (see [Pre-releases](#pre-releases)).

## Versioning (SemVer)

We follow [Semantic Versioning 2.0.0](https://semver.org/): `MAJOR.MINOR.PATCH`.

- **MAJOR** — changes that break compatibility or alter the experimental design in a
  way that makes data **not comparable** to prior versions (e.g. changed cue set,
  timing structure, or response criterion).
- **MINOR** — backward-compatible functionality (new tooling, optional flags, added
  outputs) that does not change the stimulus/timing contract of an existing run.
- **PATCH** — backward-compatible bug fixes and documentation that do not change task
  behavior.

> **Data-comparability rule of thumb:** if data collected with the new version cannot
> be pooled with data from the previous version without caveat, it is at least a MINOR
> bump and usually a MAJOR one. When in doubt, bump higher.

The version lives in two places that must stay in sync:

- `pyproject.toml` → `[project].version`
- `CHANGELOG.md` → the top heading

The git tag is the same version prefixed with `v` (e.g. `v1.2.3`). The
[release workflow](../.github/workflows/release.yml) enforces this automatically: it
fails the release if `pyproject.toml`'s version does not match the tag, or if
`CHANGELOG.md` has no heading for that version.

## Pre-releases

A version is only released **stable** once it has been thoroughly verified (see
[Verification](#verification-required-before-a-stable-release)). Until then, publish a
pre-release using a SemVer pre-release suffix:

| Suffix | Meaning |
|--------|---------|
| `-alpha.N` | Early; functionality may be incomplete. Timing **not** verified. |
| `-beta.N`  | Feature-complete, undergoing testing. Timing partially verified. |
| `-rc.N`    | Release candidate. Verification in progress / final sign-off pending. |

Examples: `v1.2.0-alpha.1`, `v1.2.0-beta.2`, `v1.2.0-rc.1`.

The [release workflow](../.github/workflows/release.yml) automatically marks any tag
carrying an `-alpha`, `-beta`, or `-rc` suffix as a **GitHub pre-release**. Tags
without a suffix are published as full releases.

Pre-release ordering follows SemVer precedence:
`1.2.0-alpha.1 < 1.2.0-beta.1 < 1.2.0-rc.1 < 1.2.0`.

## Verification required before a stable release

Do **not** drop the pre-release suffix until all of the following hold. The most
important is timing, which is verified from screen recordings, not just the CSV.

1. **Automated tests pass**, including the Octave/MATLAB calibration parity test:
   ```bash
   uv run pytest -v --ignore=tests/test_overlay.py
   ```
2. **Timing verified from screen recordings.** Record a full run with OBS configured
   for frame-accurate, frame-peekable video — Apple ProRes 422 LT, Hybrid MOV, FPS
   matching the display refresh, cursor off — per the
   [OBS recording settings in the Timing Notes](timing.md#obs-recording-settings-for-visual-auditing).
   Step through the recording frame by frame and confirm:
   - Each cue and the target render correctly and in the right order.
   - Target on-screen duration matches `target_dur_ms_actual` within one frame
     (the irreducible VSYNC quantization; see
     [Timing Notes](timing.md#why-this-cant-be-solved-in-software-frame-overshoot)).
   - No unexpected dropped frames or display glitches.
   Remember the recording is a **visual** audit; the behavioral CSV remains the
   ground truth for absolute timing and sub-frame RT
   (see [CSV timing precision vs. video recording](timing.md#csv-timing-precision-vs-video-recording)).
3. **Task measurements validated.** Inspect a full run's output CSVs and confirm the
   recorded fields (hits/misses, `rt_ms`, `target_dur_ms_actual`, `timing_drift_ms`,
   cue/condition assignment) are correct and internally consistent.
4. **Production hardware.** Verification is performed on the production environment
   (Windows + conda + scanner/DAQ where applicable), since macOS is dev-only and its
   compositor does not honor VSYNC (see
   [macOS caveat](timing.md#macos-caveat)).

If any of the above is incomplete, keep the appropriate pre-release suffix.

## Cutting a release

1. **Verify** per the checklist above (or decide on a pre-release suffix).
2. **Bump the version** in `pyproject.toml`.
3. **Update `CHANGELOG.md`**: move the entries under a new heading whose version
   matches the tag (without the leading `v`). The format follows
   [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the release workflow
   extracts this section as the release notes.
4. **Commit** the bump (e.g. `chore(release): v1.2.3`) and merge to `main`.
5. **Tag and push:**
   ```bash
   git tag v1.2.3          # or v1.2.3-rc.1 for a pre-release
   git push origin v1.2.3
   ```
6. The [release workflow](../.github/workflows/release.yml) creates a **draft** GitHub
   Release with notes pulled from `CHANGELOG.md` and the source archives attached, and
   marks it as a pre-release if the tag has an `-alpha`/`-beta`/`-rc` suffix.
7. **Review the draft** release on GitHub and publish it.

> The release is created as a **draft** so a human reviews it before it goes live —
> the final gate on the verification promise above.
