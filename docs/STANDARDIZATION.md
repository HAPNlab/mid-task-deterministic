# Standardizing task design across PsychoPy tasks

Status: **in progress**. This tracks where `mid-task-deterministic` and
[`heat-task`](https://github.com/HAPNlab/heat-task) still diverge and what belongs in
[`psyexp-core`](https://github.com/HAPNlab/psyexp-core) versus each task repo. The
consumer-side work in this repo (standard keymap schema, consuming the core
keyboard helpers, local `ExitStack` teardown) is **done** and lives in the code;
what remains below is cross-repo coordination and deliberately deferred work.

Guiding rule: **task repos keep only task-specific logic; anything a second task
would copy belongs in `psyexp-core`.**

---

## Open: align heat-task on the core manifest API

`psyexp-core` renamed `write_manifest(session_time=…)` →
`write_manifest(session_started_at=…)` in **0.8.0**. mid-task moved to 0.8.0 and
the new kwarg; **heat-task is still on 0.7.0 and still passes `session_time=`**.
So the two repos are pinned to different core majors and call the manifest writer
differently.

**Action:** bump heat-task to `psyexp-core>=0.8.0` and rename its `write_manifest`
call's kwarg to `session_started_at`; then bump to `0.9.0` and replace its
`task/phases.py` `wait_for_key`/`check_quit` with the core ones (mid-task already
does this). Keep the per-run `psyexp_core_version` in every manifest so the
resolved core is always recoverable. Treat the core's public signature as a shared
contract: a rename is a coordinated bump across all task repos in the same batch.

## Deferred: candidate core extractions

Worth centralizing eventually, but not until a second consumer makes the dedup pay
for itself:

- **§ Live-view console → `psyexp_core.console.LiveTableView`.**
  `mid_det/task/console.py::TrialLiveView` and
  `heat_task/task/console.py::SequenceLiveView` share a skeleton (a Rich `Live`
  context manager, a `_RowData` dataclass, `_make_table`, throttled `_refresh`).
  A base class would own the `Live` lifecycle and `_refresh(force=…)` throttling;
  subclasses declare columns and row rendering, with heat's status line/blink as an
  optional mixin. Low priority — the two views differ enough that the shared
  surface is mostly the container.

- **§ Teardown → shared `psyexp_core.experiment_session`.** Both tasks now wrap
  `run()` teardown in a **local** `contextlib.ExitStack` (heat derives MMS
  stop-vs-abort from `exc_type`; mid gained guaranteed teardown it previously
  lacked). Each calls `core.quit()` *after* the block so a genuine error still
  surfaces its traceback. Because `ExitStack.__exit__` fires on `BaseException`,
  Ctrl-C and the `SystemExit` from `core.quit()` both trigger teardown for free.
  Promoting this to a shared helper stays deferred until a third — or second
  hardware — task makes it worthwhile.

- **§ Operator-gated screens → core.** mid's `wait_for_start` / `run_end_screen`
  become generic only once they take a "draw this frame" callback (the inversion
  `psyexp_core.instructions.page_through` already uses). Separate extraction.

## Rejected: a `psyexp_core.runner` scaffold

Both `__main__.py::run()` functions walk a similar spine (backend → screen →
wizard → run dir + logging → stimuli → manifest → instructions → loop → end →
cleanup), which tempts a "extract one `run()` scaffold and pass hooks" design.
**Don't** — the similarities are cosmetic and the differences are load-bearing:

- **Ordering inverts.** mid opens the screen *before* the wizard (the wizard needs
  the measured frame duration for its RT-field defaults); heat runs the wizard
  *first* (it returns `screen_index` and must precede the window). A scaffold with
  fixed `wizard`/`screen` slots is wrong for one task no matter which order it picks.
- **Teardown is asymmetric.** heat chooses MMS `abort` vs `stop` on the way out (a
  thermode left running is a safety issue); mid just closes CSV writers.
- **The middles are genuinely task-specific** (scanner pulse-counter + adaptive
  calibration + flip-patch vs. background `StatusPoller` + MMS program-select) and
  interleave differently.

So `run()` stays per-task: an explicit top-to-bottom script you can follow beats
indirection through a framework, and the reuse comes from shared *leaf* helpers
(`screen.setup_screen`, a frame-rate resolver, `rundir.make_run_dir`,
`write_manifest`, `wait_for_key`, the eventual `LiveTableView`), not an
orchestrator. *Library, not framework.* What stays duplicated is ~15 lines of glue
— the order the helpers are called in — not logic.

## Left as-is: hand-rolling is correct

Considered replacing with a library, but the hand-rolled version is the right call:

- **`StatusPoller` exponential backoff (heat `task/status.py`) → tenacity/backoff?**
  No. The bounded backoff is ~3 lines and is coupled to `stop_event.wait()` for
  prompt cancellation; retry libraries wrap a *callable* and don't fit a
  long-lived, stop-event-interruptible reconnect-and-stream loop.
- **`sum(x) / len(x)` rolling means (heat `phase_tracker.py`) → numpy?** No. They
  run per-sample over ~5-element windows; building an ndarray each sample is slower.
  numpy is correctly reserved for the calibration array.
- **Plain `@dataclass` CSV-row records → pydantic?** No. Internal records with no
  validation need; pydantic would be pure overhead.
