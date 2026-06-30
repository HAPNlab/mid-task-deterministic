# Standardizing task design across PsychoPy tasks

Status: **proposal**. This documents where `mid-task-deterministic` and
[`heat-task`](https://github.com/HAPNlab/heat-task) still diverge, the shared
design we should converge on, and what belongs in
[`psyexp-core`](https://github.com/HAPNlab/psyexp-core) versus each task repo.

The PR that introduced this file already applied the **consumer-side** half
(everything that lives in this repo). The **core-side** half — moving shared code
into `psyexp-core` so the duplication is actually deleted, not just made
consistent — is sequenced in [Migration plan](#migration-plan) and needs a
`psyexp-core` release plus a matching change in `heat-task`.

Guiding rule: **task repos keep only task-specific logic; anything a second task
would copy belongs in `psyexp-core`.** A divergence is "a thing the next task
author has to re-decide." Each one below is small on its own; the cost is that
they compound across tasks.

---

## 1. Keyboard bindings (keymaps)

The original trigger for this doc. The two tasks defined keymaps differently:

| | mid-task (before) | heat-task |
|---|---|---|
| value type | `dict[str, str]` (one key) | `dict`/`list[str]` (many keys) |
| numpad / button-box variants | none | `num_1`, `num_0` included |
| quit key | `"end": "escape"` inside the dict | dedicated `QUIT_KEYS` |
| fMRI vs behavioral | two identical dicts (`KEYS_FMRI`/`KEYS_BEHAVIORAL`) | single set |
| on-screen label | the single string | `KEYS[0]` (canonical) |

**Standard schema** (now adopted in `mid_det/config.py`, matching heat-task):

```python
INSTRUCTION_KEYS: dict[str, list[str]] = {"forward": ["1", "num_1"], "back": []}
START_KEYS: list[str] = ["0", "num_0"]   # begin the run (non-fMRI)
END_KEYS:   list[str] = ["0", "num_0"]   # dismiss the end screen / exit
QUIT_KEYS:  list[str] = ["escape"]       # abort at any prompt
```

Rules of the schema:

1. **Every action maps to a `list[str]`.** Single keys are length-1 lists.
2. **`list[0]` is canonical** — the key echoed on screen and in logs.
3. **Numpad / button-box aliases live in the list** (`num_0` next to `0`), so a
   scanner button box that reports `num_1` works without touching call sites.
4. **`QUIT_KEYS` is its own binding**, not smuggled in as `"end"`. The shared
   keyboard helpers append it, so escape-to-quit is uniform and never hardcoded.
5. **Participant response keys are separate** from operator/navigation keys
   (`RESPONSE_KEYS` here; heat-task has no participant keypresses).

This schema is currently duplicated (identically) in both `config.py` files. It
is a small, stable vocabulary and a good first thing to host in
`psyexp_core.keys` as a `TypedDict` / dataclass plus validation, with each task
supplying the literal key names.

## 2. Keyboard helpers (`wait_for_key`, `check_quit`, …)

Both tasks wrap `psyexp_core.keyboard` the same way:

- heat-task: `task/phases.py` → `wait_for_key`, `check_quit`, `wait_for_start`,
  `run_end_screen`.
- mid-task: `ratings/__main__.py::_wait_keys` (= `wait_for_key` + quit) and
  `task/phases.py::_poll_hotkeys` (quit + overlay toggle).

**Done (core v0.9.0).** `wait_for_key(kb, key_list, *, quit_keys=(),
clear_first=True, on_quit=…)` and `check_quit(kb, quit_keys, *, on_quit=…)` now
live in `psyexp_core.keyboard`, parameterized by each task's quit keys (the quit
action defaults to `psychopy.core.quit`, injectable for tests). mid-task's
short-lived `mid_det/keyboard.py` shim was deleted and `ratings/__main__.py` calls
the core helpers directly; heat-task's local `wait_for_key`/`check_quit` in
`task/phases.py` were removed in favour of the core ones (`sequence.py` calls
`check_quit(kb, config.QUIT_KEYS)`).

Still correctly task-local: mid's `_poll_hotkeys` (device-direct `get_presses` in
the timing hot loop) and the operator-gated screens (`wait_for_start`,
`run_end_screen`) — generic only once they take a "draw this frame" callback (the
inversion `psyexp_core.instructions.page_through` already uses); a worthwhile but
separate extraction.

## 3. Setup wizard

Shared today, copy-pasted:

- `_SUBJECT_PLACEHOLDER = "XXX000"` is defined in both repos (mid-task's ratings
  wizard already imports it from the main wizard — good; heat-task redefines it).
- The `subject_id = ask_text("Subject ID", placeholder=…).strip() or PLACEHOLDER`
  idiom appears in three wizards.
- Each repo has a `SessionInfo` dataclass with overlapping fields
  (`subject_id`, `show_instructions`, screen/run identifiers).

**Proposal:** host the placeholder constant and a `prompt_subject_id()` helper in
`psyexp_core.wizard`, and offer a small `SessionInfoBase` (subject_id +
show_instructions) that task `SessionInfo`s extend. Task-specific fields
(`fmri`, `base_rt_s`, `host`/`port`, `run_file`) stay in each task.

## 4. Live-view console

`mid_det/task/console.py::TrialLiveView` and
`heat_task/task/console.py::SequenceLiveView` share a skeleton: a Rich `Live`
wrapped in a context manager, a `_RowData` dataclass, a `_make_table`, and a
throttled `_refresh`. heat-task's adds a status line, heartbeat blink, and
latency chip.

**Proposal:** a `psyexp_core.console.LiveTableView` base owning the `Live`
lifecycle (`__enter__`/`__exit__`), the row list, and `_refresh(force=…)`
throttling. Subclasses declare columns and how a row renders. The status
line/blink is an optional mixin. Lower priority than 1–3 (the two views differ
enough that the shared surface is mostly the container).

## 5. Manifest writer — align the core API

`psyexp-core` renamed `write_manifest(session_time=…)` →
`write_manifest(session_started_at=…)` in **0.8.0**. mid-task moved to 0.8.0 and
the new kwarg; **heat-task is still on 0.7.0 and still passes `session_time=`**.
So the two repos are pinned to different core majors and call the manifest writer
differently.

**Proposal:** bump heat-task to `psyexp-core>=0.8.0` and rename its
`write_manifest` call's kwarg to `session_started_at`. Keep the per-run
`psyexp_core_version` in every manifest (already done) so the resolved core is
always recoverable. Going forward, treat the core's public signature as a shared
contract: a rename is a coordinated bump across all task repos in the same batch.

## 6. Entry-point skeleton (`run()`)

Both `__main__.py::run()` functions walk a similar spine: configure backend →
screen + frame rate → wizard → run dir + logging → session summary → stimuli +
keyboard → manifest → instructions → wait for start → live-view loop → end
screen → cleanup. It is tempting to read that as "extract one `run()` scaffold
and pass hooks." **Don't** — the spine's similarities are cosmetic and its
differences are load-bearing:

- **Ordering inverts.** mid opens the screen *before* the wizard
  (`run_wizard(frame_dur_s=…)` needs the measured frame duration for its RT-field
  defaults); heat runs the wizard *first* (it returns the `screen_index` and must
  precede the window so the operator can arm the MMS). A scaffold with fixed
  `wizard`/`screen` slots is wrong for one task no matter which order it picks.
- **Teardown is asymmetric.** heat wraps the whole loop in `try/except/finally`
  and, on the way out, chooses MMS `abort` vs `stop` (a thermode left running is a
  safety issue). mid just closes four CSV writers. One imposed loop shape either
  burdens mid with machinery it doesn't need or denies heat the guaranteed
  teardown it does.
- **The middles are genuinely task-specific.** Scanner pulse-counter + adaptive
  calibration + debug-overlay flip-patch (mid) vs. background `StatusPoller` +
  MMS program-select + START-coupled-to-the-start-key (heat). These aren't the
  same hook at the same point; they interleave differently.

So a `psyexp_core.runner` that sequences phases and calls task hooks is the wrong
shape. Two flexible alternatives instead:

### (a) Leave `run()` per-task, built from shared leaf helpers — *default*

Each task keeps its own top-to-bottom `run()`; the reuse comes entirely from the
leaf utilities in §1–§5 (`screen.setup_screen`, a frame-rate resolver,
`rundir.make_run_dir`, `write_manifest`, `wait_for_key`, `LiveTableView`). What
stays duplicated is ~15 lines of *glue* — the order those helpers are called in —
not logic.

This is the right default because `run()` is read far more than it is written: an
explicit script you can follow end-to-end beats indirection through a framework,
and the ordering differences above stop being a problem when they are just
different lines in different files. *Library, not framework.*

- **Cost:** the call sequence looks similar across tasks (though never identical,
  per the ordering point) — some apparent boilerplate remains.
- **Benefit:** zero coupling; each `run()` is a literal, greppable record of that
  experiment, and a new task can diverge freely without fighting an abstraction.

### (b) A teardown-owning context manager — *opt in when cleanup gets critical*

The one piece genuinely worth centralizing is **guaranteed teardown**: flush
logging, close the window, quit, and run task-registered cleanups — on normal
exit *and* on Ctrl-C, a quit-key `SystemExit`, or a mid-run error. heat already
hand-rolls this; the next hardware task should not have to re-derive it.

A context manager owns *only* that, and nothing about ordering or the loop — and
it needs no bespoke class, because the stdlib's `contextlib.ExitStack` already
*is* this primitive. Pre-register the PsychoPy bookends and hand the stack back:

```python
# psyexp_core.session
from contextlib import ExitStack, contextmanager

@contextmanager
def experiment_session(win):
    """Guarantee teardown on any exit — normal, Ctrl-C, a quit-key SystemExit, or
    a mid-run error. Yields the ExitStack so the task registers its own cleanups:
      stack.callback(fn) -> always runs (LIFO); can't see or suppress the exception
      stack.push(fn)     -> fn(exc_type, exc, tb); lets you branch on abnormal exit
    """
    with ExitStack() as stack:
        stack.callback(core.quit)      # bookends run last (LIFO):
        stack.callback(win.close)      #   flush -> close -> quit
        stack.callback(logging.flush)
        yield stack
```

Because `ExitStack.__exit__` fires on `BaseException`, both Ctrl-C
(`KeyboardInterrupt`) and the `SystemExit` that `core.quit()` raises trigger
teardown for free — heat's hand-rolled `try/except` has to name those explicitly.

The task still builds the window and writes its own setup/loop; it just registers
what must be torn down:

```python
# mid-task
with experiment_session(win) as stack:
    stack.callback(writers.close)
    ...                                  # screen -> framerate -> wizard -> loop, as today

# heat-task
def _abort(exc_type, exc, tb):
    if exc_type is not None:             # any abnormal exit (error / Ctrl-C / quit key)
        halt_mms("abort")               # thermode safety
    return False                         # never suppress

with experiment_session(win) as stack:
    stack.callback(poller.stop)
    stack.callback(writers.close)
    stack.push(_abort)
    ...
    run_sequences(...)
    halt_mms("stop")                     # clean path: normal stop
```

This captures heat's safety-critical `finally` without dictating the order of
anything else, and mid opts into the same guarantee for one `stack.callback`. It
**composes with (a)** rather than replacing it — the body of the `with` is still a
per-task `run()` made of §1–§5 helpers. (Friendly `on_teardown` / `on_abort`
aliases are trivial sugar over `callback` / `push` if the raw names read poorly.)

**Status:** both tasks now wrap their `run()` teardown in a **local** `ExitStack`
(heat dropped its `try/finally` + `halted_cleanly` flag and derives MMS stop-vs-
abort from `exc_type`; mid gained the guaranteed teardown it previously lacked).
Each calls `core.quit()` *after* the block so a genuine error still surfaces its
traceback. Promoting this to a **shared** `psyexp_core.experiment_session` helper
(the sketch above) stays deferred until a third — or second hardware — task makes
the dedup worthwhile. The phase-sequencing orchestrator stays rejected.

---

## Migration plan

1. **(this PR)** Consumer-side consistency in mid-task: standard keymap schema,
   `mid_det/keyboard.py`, and todo cleanup. No core release needed.
2. **psyexp-core `0.9.0`**: add `psyexp_core.keys` (schema) and the generalized
   `wait_for_key`/`check_quit` (+ optional `wait_for_start`/`end_screen`); add
   the wizard helpers (§3).
3. **mid-task**: depend on `0.9.0`; delete `mid_det/keyboard.py`, import the
   helpers from core; drop the duplicated placeholder/idioms.
4. **heat-task**: bump to `>=0.8.0` first to fix the manifest kwarg (§5), then to
   `0.9.0`; replace its `phases.py` helpers with the core ones.
5. **psyexp-core `0.10.0`** (optional): `LiveTableView` (§4). Both tasks already
   use a *local* `ExitStack` for teardown (§6b); consolidating that into a shared
   `experiment_session` helper is deferred until a second hardware task needs it.
   The phase-sequencing runner is explicitly **not** planned; `run()` stays
   per-task (§6a).

Sequencing keeps each step small and independently shippable, and never leaves a
task repo importing a core symbol that isn't released yet.

---

## Appendix: hand-rolled vs. library

A pass over all three repos for code that reimplements what a library already
does. The codebases are mostly disciplined here — `conditions.py` (tomllib +
pydantic), `recording.py` (`csv.DictWriter`), `manifest.py` (pydantic +
`py-cpuinfo`), `screen/setup.py` (`numpy` percentiles), and the medoc CLI
(`argparse`) all reach for the right tool — so this is short.

**Fixed**

- **heat-task `last_connection` persistence → pydantic.** `io/setup_wizard.py`
  hand-rolled `json.load` + per-field `isinstance` checks + a `TypedDict`, in the
  same package that validates run files with pydantic in `conditions.py`. Now a
  `LastConnection(BaseModel)` with `model_validate_json` / `model_dump_json`
  (pydantic is already a dependency). Fixes a latent bug en route: the old
  `.get("screen")` + naive truthiness default would have dropped screen index `0`.

**Adopt with the core extraction (§2 / §6b)**

- **Prompt waits + quit → `psyexp_core.keyboard`.** `wait_for_key` / `check_quit`
  were duplicated in heat's `task/phases.py` and mid's `mid_det/keyboard.py`; now
  hosted in core (v0.9.0), parameterized by each task's quit keys.
- **Teardown → `contextlib.ExitStack`.** heat's `__main__` hand-rolls
  `try/except (KeyboardInterrupt, SystemExit, Exception)/finally` + a
  `halted_cleanly` flag; that is exactly `ExitStack` (see §6b), which also covers
  the `BaseException` paths for free.

**Considered, but hand-rolling is correct (left as-is)**

- **`StatusPoller` exponential backoff (`task/status.py`) → tenacity/backoff?**
  No. The bounded backoff is ~3 lines and is coupled to `stop_event.wait()` for
  prompt cancellation; retry libraries wrap a *callable* and don't fit a
  long-lived, stop-event-interruptible reconnect-and-stream loop. The surrounding
  `threading` + `queue.SimpleQueue` are already the right primitives.
- **`sum(x) / len(x)` rolling means (`phase_tracker.py`) → numpy?** No. They run
  per-sample over ~5-element windows; building an ndarray each sample is slower.
  numpy is correctly reserved for the calibration array.
- **Plain `@dataclass` CSV-row records → pydantic?** No. Internal records with no
  validation need; pydantic would be pure overhead.
