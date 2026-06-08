"""
PsychoPy widget construction and draw helpers for the cue-ratings survey.
No clocks, no response logic, no I/O (same contract as mid_det.display).

Layout (height units): the cue sits near the top, the 7-circle scale runs
horizontally across the middle, legend anchors below it, and a control-hint line
at the bottom.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from psychopy import visual

from mid_det import config
from mid_det.task.display import _LINE_Y_FRAC
from mid_det.ratings import core

# ── Layout constants (height units; screen spans −0.5…+0.5) ──────────────────
_CUE_Y = 0.30          # cue group vertical centre (raised to clear the title)
_SCALE_Y = -0.08       # scale circles vertical centre
_LEGEND_Y = -0.20      # legend anchor labels
_TITLE_Y = 0.02        # scale title ("VALENCE"/"AROUSAL"), just above circles
_INSTR_Y = -0.40       # bottom control-hint line
_SCALE_X_HALF = 0.55   # circles span x ∈ [-0.55, +0.55]
_CIRCLE_R = 0.035
_SLIDER_R = _CIRCLE_R * 2.0 / 3.0
_CUE_R = 0.1           # matches mid_det.display cue_radius

_INSTR_TEXT = "Move  <  >  with 1 and 2, then press 3 to select"


def _circle_x(i: int) -> float:
    """Centre x of scale circle *i* (0-based, 7 circles evenly spaced)."""
    step = (2 * _SCALE_X_HALF) / (core.N_ELS - 1)
    return -_SCALE_X_HALF + step * i


@dataclass
class RatingStimuli:
    win: visual.Window
    scale_circles: list[visual.Circle]
    slider: visual.Circle
    title: visual.TextStim
    legend: list[visual.TextStim]
    instr: visual.TextStim
    fix: visual.TextStim
    # Cue components (reused from the MID display scheme, positioned high)
    cue_circle: visual.Circle
    cue_square: visual.Rect
    cue_line: visual.Line
    cue_label: visual.TextStim


def _to_rgb255(colors):
    return [list(c) for c in colors]


def build_rating_stimuli(win: visual.Window) -> RatingStimuli:
    win_res = win.size
    x_scr = float(win_res[0]) / float(win_res[1])
    font_h = 1.0 / 20
    text_col = "white"

    scale_circles = [
        visual.Circle(
            win, name=f"scale_{i}", radius=_CIRCLE_R, pos=(_circle_x(i), _SCALE_Y),
            fillColor=(0, 0, 0), lineColor=None, colorSpace="rgb255",
            edges=64, autoLog=False,
        )
        for i in range(core.N_ELS)
    ]
    slider = visual.Circle(
        win, name="slider", radius=_SLIDER_R, pos=(_circle_x(0), _SCALE_Y),
        fillColor="black", lineColor="white", lineWidth=2, edges=64, autoLog=False,
    )
    title = visual.TextStim(
        win, name="rating_title", font="Arial", pos=(0, _TITLE_Y),
        height=font_h * 1.4, color=text_col, autoLog=False,
    )
    legend = [
        visual.TextStim(
            win, name=f"legend_{j}", font="Arial",
            pos=(-_SCALE_X_HALF + _SCALE_X_HALF * j, _LEGEND_Y),
            height=font_h * 0.8, color=text_col, autoLog=False,
        )
        for j in range(3)
    ]
    instr = visual.TextStim(
        win, name="rating_instr", font="Arial", text=_INSTR_TEXT,
        pos=(0, _INSTR_Y), height=font_h * 0.85, color=text_col,
        wrapWidth=x_scr / 1.2, autoLog=False,
    )
    fix = visual.TextStim(
        win, name="rating_fix", text="+", pos=(0, 0),
        height=font_h * 4, color=text_col, autoLog=False,
    )

    cue_circle = visual.Circle(
        win, name="rcue_circle", radius=_CUE_R, pos=(0, _CUE_Y),
        lineColor="white", fillColor=None, lineWidth=4, edges=64, autoLog=False,
    )
    cue_square = visual.Rect(
        win, name="rcue_square", width=_CUE_R * 2, height=_CUE_R * 2, pos=(0, _CUE_Y),
        lineColor="white", fillColor=None, lineWidth=4, autoLog=False,
    )
    cue_line = visual.Line(
        win, name="rcue_line", start=(-_CUE_R, _CUE_Y), end=(_CUE_R, _CUE_Y),
        lineColor="white", lineWidth=4, autoLog=False,
    )
    cue_label = visual.TextStim(
        win, name="rcue_label", font="Arial",
        pos=(0, _CUE_Y - _CUE_R - font_h * 1.2), height=font_h * 1.2,
        color=text_col, autoLog=False,
    )

    return RatingStimuli(
        win=win, scale_circles=scale_circles, slider=slider, title=title,
        legend=legend, instr=instr, fix=fix, cue_circle=cue_circle,
        cue_square=cue_square, cue_line=cue_line, cue_label=cue_label,
    )


def _draw_cue(stim: RatingStimuli, cue: core.RatingCue) -> None:
    """Draw the cue (shape + magnitude line + dollar label) near the top.
    Mirrors mid_det.display.draw_cue geometry but at the raised cue position."""
    if config.POLARITY_SHAPE[cue.polarity] == "circle":
        radius = stim.cue_circle.radius
        stim.cue_circle.draw()
    else:
        radius = stim.cue_square.width / 2
        stim.cue_square.draw()

    y_frac = _LINE_Y_FRAC[cue.magnitude]
    if config.POLARITY_SHAPE[cue.polarity] == "circle" and y_frac != 0.0:
        half_chord = radius * (1.0 - y_frac * y_frac) ** 0.5
    else:
        half_chord = radius
    y = _CUE_Y + y_frac * radius
    stim.cue_line.start = (-half_chord, y)
    stim.cue_line.end = (+half_chord, y)
    stim.cue_line.draw()

    stim.cue_label.text = config.cue_label(cue.polarity, cue.magnitude)
    stim.cue_label.draw()


def draw_scale(
    stim: RatingStimuli,
    scale: str,
    slidepos: int,
    cue: core.RatingCue | None = None,
) -> None:
    """Draw one rating screen. *slidepos* is 1-based (1..N_ELS).
    If *cue* is given, the cue is drawn above the scale (real trial);
    if None, only the scale is drawn (practice demo). Caller flips."""
    colors = (
        core.VALENCE_COLORS_255 if scale == "valence" else core.AROUSAL_COLORS_255
    )
    for c, col in zip(stim.scale_circles, colors):
        c.fillColor = list(col)
        c.draw()

    stim.slider.pos = (_circle_x(slidepos - 1), _SCALE_Y)
    stim.slider.draw()

    stim.title.text = core.SCALE_TITLES[scale]
    stim.title.draw()
    for label_stim, txt in zip(stim.legend, core.SCALE_LEGENDS[scale]):
        label_stim.text = txt
        label_stim.draw()
    stim.instr.draw()

    if cue is not None:
        _draw_cue(stim, cue)


def draw_fixation(stim: RatingStimuli) -> None:
    stim.fix.draw()
