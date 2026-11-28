"""Speed study (UNSCORED, pilot seed 29001; read-only): where does a G2 trial's time go? Profiles the scene build and
start sequence (about 7,200 control steps), then times 2,000 further control steps with the magnet callback on and off.
Writes nothing in the repository."""
import cProfile
import importlib.util
import io
import pstats
import sys
from pathlib import Path
import time

import mujoco

spec = importlib.util.spec_from_file_location("trials", Path(__file__).resolve().parents[1] / "E8_scored_g2" / "trials.py")
T = importlib.util.module_from_spec(spec)
sys.modules["trials"] = T
spec.loader.exec_module(T)

T.configure({}, T.start_draw(29001))
pr = cProfile.Profile()
t0 = time.perf_counter()
pr.enable()
r = T.TA.TwoArm(T.L, T.HC, T.DEFAULTS["grip"])
pr.disable()
t_build = time.perf_counter() - t0
st = r.magnet_stats()
print(f"build + start sequence: {t_build:.1f} s wall, {r.d.time:.2f} s sim, {st['steps']} control steps "
      f"-> {st['steps'] / t_build:.0f} steps/s overall")
s = io.StringIO()
pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(18)
print(s.getvalue()[:6000])


def timed(n, label):
    t = time.perf_counter()
    r.ctrl_step(n)
    dt = time.perf_counter() - t
    print(f"{label}: {n} steps in {dt:.2f} s -> {n / dt:.0f} steps/s ({r.m.opt.timestep * n / dt:.3f}x real time)")
    return dt


on = timed(2000, "magnets ON ")
T.MagnetSystem.uninstall()
off = timed(2000, "magnets OFF")
print(f"magnet share of step time ~ {(on - off) / on:.0%}")
# controller cost alone (no physics step): impedance + J7 law
t = time.perf_counter()
for _ in range(2000):
    r.impedance()
    r.j7_control()
print(f"controllers only: {2000 / (time.perf_counter() - t):.0f} evaluations/s")
t = time.perf_counter()
for _ in range(2000):
    mujoco.mj_step(r.m, r.d)
print(f"raw mj_step (no controllers, no magnets, no audit): {2000 / (time.perf_counter() - t):.0f} steps/s")
