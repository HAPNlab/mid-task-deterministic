"""Quick visual test for debug overlay positioning. Run with: uv run python test_overlay.py"""
from psychopy import core, visual

win = visual.Window(size=[1280, 800], fullscr=False, units="height", color=(-1, -1, -1))

stim = visual.TextStim(
    win,
    text="[DEBUG]  sub:XXX000  run:practice  fmri:N\ntrial:3/54  phase:response\ncue:gain $5  win:265 ms  jitter:482 ms\nhits:2/3 (67%)  earned:$10  pulse:7\nlast:HIT  RT:124 ms  drift:+2.3 ms\nt:14.823 s  sched:14.000 s",
    pos=(-0.6, 0.2),
    height=0.05,
    color="yellow",
)

for _ in range(120):
    stim.draw()
    win.flip()

win.close()
core.quit()
