<!--
Thanks for contributing! Please fill out each section.
See CONTRIBUTING.md for the full process.
-->

## Summary

<!-- What does this PR do, and why? -->

## Related issue

<!-- e.g. Closes #123 -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactor / internal
- [ ] Task design / timing change (affects collected data)

## How was this tested?

<!-- Commands run, environments, and any manual display/scanner verification. -->

```bash
uv run pytest -v --ignore=tests/test_overlay.py
```

## Checklist

- [ ] Tests pass (`uv run pytest`), including the Octave/MATLAB parity test where an engine is available.
- [ ] Changes are headless/CI safe — logic & timing tests run without PsychoPy or a display (no hard top-level `import psychopy` in tested modules).
- [ ] Documentation and `CHANGELOG.md` are updated.
- [ ] Changes work under both the UV (`uv.lock`) and conda (`environment.yml`) workflows; dependency changes are reflected in both `pyproject.toml` and `environment.yml`.
- [ ] I linked the related issue and kept this PR focused on a single concern.
