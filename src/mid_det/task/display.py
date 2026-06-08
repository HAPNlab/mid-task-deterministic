"""
PsychoPy visual component construction and draw helpers.
No clocks, no response logic, no I/O.

Cue rendering follows the fmo-task scheme:
  - Circle (polarity=gain) or Square (polarity=loss) outline
  - A horizontal line across the shape at top / middle / bottom for
    magnitude 5 / 1 / 0 (line indicates where the "fill" level would be)
  - Dollar-amount text label below the shape
"""
from __future__ import annotations

from dataclasses import dataclass

try:
    from psychopy import visual
except ModuleNotFoundError:  # headless/CI without PsychoPy; only needed to build stimuli
    visual = None  # type: ignore[assignment]

from mid_det import config


# Line Y-offset (in shape-radius units) per magnitude: 0 = low, 1 = mid, 5 = top.
_LINE_Y_FRAC: dict[int, float] = {0: -0.707, 1: 0.0, 5: +0.707}


@dataclass
class Stimuli:
    win: visual.Window
    fix_x: visual.TextStim
    fix_o: visual.TextStim
    cue_circle: visual.Circle
    cue_square: visual.Rect
    cue_line: visual.Line
    cue_label: visual.TextStim
    target: visual.Polygon
    feedback_amount: visual.TextStim
    instr_prompt: visual.TextStim
    instr_first: visual.TextStim
    instr_finish: visual.TextStim
    wait: visual.TextStim
    end: visual.TextStim


def build_stimuli(win: visual.Window) -> Stimuli:
    """Construct all visual stimuli and return a Stimuli dataclass."""
    y_scr = 1.0
    win_res = win.size
    x_scr = float(win_res[0]) / float(win_res[1])
    font_h = y_scr / 20
    trial_font_h = y_scr / 15  # Font size for cue label and outcome feedback (larger than instructions)
    wrap_w = x_scr / 1.5
    text_col = "white"

    cue_radius = 0.14

    fix_x = visual.TextStim(
        win, name="fix_x", pos=(0, 0), text="x", height=font_h * 2, color=text_col,
        autoLog=False,
    )
    fix_o = visual.TextStim(
        win, name="fix_o", pos=(0, 0), text="o", height=font_h * 2, color=text_col,
        autoLog=False,
    )

    # Circle and square cue shapes (drawn conditionally per trial)
    cue_circle = visual.Circle(
        win, name="cue_circle", radius=cue_radius, pos=(0, 0),
        lineColor="white", fillColor=None, lineWidth=4, edges=64,
        autoLog=False,
    )
    cue_square = visual.Rect(
        win, name="cue_square", width=cue_radius * 2, height=cue_radius * 2, pos=(0, 0),
        lineColor="white", fillColor=None, lineWidth=4,
        autoLog=False,
    )
    # Magnitude line drawn on top of the shape outline.
    cue_line = visual.Line(
        win, name="cue_line",
        start=(-cue_radius, 0.0), end=(cue_radius, 0.0),
        lineColor="white", lineWidth=4,
        autoLog=False,
    )

    cue_label = visual.TextStim(
        win, name="cue_label", font="Arial",
        pos=(-0.006, -cue_radius - trial_font_h),
        height=trial_font_h, color=text_col,
        autoLog=False,
    )

    target = visual.Polygon(
        win, name="target", edges=3, radius=0.14, fillColor="white", lineWidth=0, pos=(0, 0),
        autoLog=False,
    )

    feedback_amount = visual.TextStim(
        win, name="feedback_amount", font="Arial", pos=(0, 0),
        height=trial_font_h + y_scr / 30, wrapWidth=None, color=text_col,
        autoLog=False,
    )

    instr_prompt = visual.TextStim(
        win, name="instr_prompt", font="Arial", pos=(0, y_scr / 10),
        height=font_h, wrapWidth=wrap_w, color=text_col,
        autoLog=False,
    )
    keys_map = config.KEYS_BEHAVIORAL  # updated per session in update_instr_keys
    instr_first = visual.TextStim(
        win, name="instr_first", text=f"Press {keys_map['forward']} to continue.",
        height=font_h, color=text_col, pos=(0, -y_scr / 4),
        autoLog=False,
    )
    instr_finish = visual.TextStim(
        win, name="instr_finish",
        text=(
            "You have reached the end of the instructions. "
            "When you are ready to begin the task, place your fingers on the "
            "keys and notify the experimenter."
        ),
        height=font_h, color=text_col, pos=(0, 0), wrapWidth=wrap_w,
        autoLog=False,
    )

    wait = visual.TextStim(
        win, name="wait", pos=(0, 0),
        text="Get ready!",
        height=font_h, color=text_col, wrapWidth=wrap_w,
        autoLog=False,
    )
    end = visual.TextStim(
        win, name="end", pos=(0, 0), text="Thank you!", height=font_h, color=text_col,
        wrapWidth=wrap_w, autoLog=False,
    )

    return Stimuli(
        win=win,
        fix_x=fix_x,
        fix_o=fix_o,
        cue_circle=cue_circle,
        cue_square=cue_square,
        cue_line=cue_line,
        cue_label=cue_label,
        target=target,
        feedback_amount=feedback_amount,
        instr_prompt=instr_prompt,
        instr_first=instr_first,
        instr_finish=instr_finish,
        wait=wait,
        end=end,
    )


def update_instr_keys(stimuli: Stimuli, fmri: bool) -> None:
    """Update instruction navigation key labels based on run mode."""
    keys_map = config.KEYS_FMRI if fmri else config.KEYS_BEHAVIORAL
    stimuli.instr_first.text = f"Press {keys_map['forward']} to continue."


def draw_cue(stimuli: Stimuli, polarity: str, magnitude: int) -> None:
    """Draw the trial cue: shape + magnitude line + dollar label."""
    # Shape body
    if config.POLARITY_SHAPE[polarity] == "circle":
        radius = stimuli.cue_circle.radius
        stimuli.cue_circle.draw()
    else:
        radius = stimuli.cue_square.width / 2
        stimuli.cue_square.draw()

    # Magnitude line (position encodes 0 / 1 / 5 as low / mid / high)
    y_frac = _LINE_Y_FRAC[magnitude]
    # For circles the line is a chord, so its x extent shrinks away from the
    # center to stay inside the circle. For squares it spans the full width.
    if config.POLARITY_SHAPE[polarity] == "circle" and y_frac != 0.0:
        half_chord = radius * (1.0 - y_frac * y_frac) ** 0.5
    else:
        half_chord = radius
    y = y_frac * radius
    stimuli.cue_line.start = (-half_chord, y)
    stimuli.cue_line.end = (+half_chord, y)
    stimuli.cue_line.draw()

    # Dollar label
    stimuli.cue_label.text = config.cue_label(polarity, magnitude)
    stimuli.cue_label.draw()


def draw_fixation_x(stimuli: Stimuli) -> None:
    """Within-trial fixation glyph (matches MATLAB fixation phase + pre-target buffer)."""
    stimuli.fix_x.draw()


def draw_fixation_o(stimuli: Stimuli) -> None:
    """ITI / leadin / leadout fixation glyph (matches MATLAB DisplayITI 'o')."""
    stimuli.fix_o.draw()


def draw_target(stimuli: Stimuli) -> None:
    stimuli.target.draw()


def draw_feedback(stimuli: Stimuli, hit: bool, reward_outcome: str) -> None:
    stimuli.feedback_amount.text = reward_outcome
    stimuli.feedback_amount.draw()
