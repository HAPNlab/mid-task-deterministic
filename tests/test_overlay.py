"""Quick visual test for debug overlay positioning. Run with: uv run python test_overlay.py
Controls:
  Arrow keys  — move position
  + / -       — increase / decrease font height
  q / Escape  — quit and print final values
"""
from psychopy import core, visual
from psychopy.hardware import keyboard

win = visual.Window(size=[1280, 800], fullscr=False, units="height", color=(-1, -1, -1))
kb = keyboard.Keyboard()

px, py = -0.2, 0.65
h = 0.02
step_pos = 0.02
step_h = 0.002

stim = visual.TextStim(
    win,
    text="[DEBUG]  sub:XXX000  run:practice  fmri:N\ntrial:3/54  phase:response\ncue:gain $5  win:265 ms  jitter:482 ms\nhits:2/3 (67%)  earned:$10  pulse:7\nlast:HIT  RT:124 ms  drift:+2.3 ms\nt:14.823 s  sched:14.000 s",
    pos=(px, py),
    height=h,
    color="yellow",
    font="Courier",
    alignText="left",
)

def update():
    stim.pos = (px, py)
    stim.height = h
    print(f"pos=({px:.3f}, {py:.3f})  height={h:.4f}", flush=True)

while True:
    keys = kb.getKeys(keyList=["escape", "q", "left", "right", "up", "down", "equal", "minus"], waitRelease=False)
    changed = False
    for k in keys:
        if k.name in ("escape", "q"):
            print(f"\nFinal: pos=({px:.3f}, {py:.3f})  height={h:.4f}")
            win.close()
            core.quit()
        elif k.name == "left":  px -= step_pos; changed = True
        elif k.name == "right": px += step_pos; changed = True
        elif k.name == "up":    py += step_pos; changed = True
        elif k.name == "down":  py -= step_pos; changed = True
        elif k.name == "equal": h += step_h;    changed = True
        elif k.name == "minus": h = max(0.01, h - step_h); changed = True
    if changed:
        update()
    stim.draw()
    win.flip()
