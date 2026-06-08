# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v1.0.0-rc.2

### Added

- Legacy data format support for backward compatibility with prior runs.
- `trial_type`, `polarity`, and `magnitude` columns to the scan log CSV.
- Rejection of unmapped `(polarity, magnitude)` pairs at sequence load.
- MIT License.
- Contributing guide, issue/PR templates, and a release guide.
- CI check verifying the `uv` lock file stays synchronized.

### Changed

- **Breaking:** ratings output filename template changed from
  `<subject>_ratings.csv` to `ratings_<subject>.csv`.
- Reorganized `mid_det` into `task/` and `io/` subpackages.
- Split `trial.py` into focused modules and simplified `run_response`.
- Named display refresh-rate bounds as configuration constants.

### Fixed

- Warm up the GPU before VSYNC calibration rather than after.
- Match on-screen instructions to the original MATLAB task.

## v1.0.0-rc.1

Initial release candidate for version 1.0.0.