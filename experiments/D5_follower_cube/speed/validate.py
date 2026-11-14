"""Validate a D5 speed variant (UNSCORED): 3 s rest (valid+solved) and the rig sequence
"U R U' R' F F'" with the unchanged M1 pad rig; every observed move must match. Reports steps/s.
Usage: uv run python experiments/D5_follower_cube/speed/validate.py <variant>"""
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from variants import xml_for  # noqa: E402

from rubiknetic.cube_logic import parse  # noqa: E402
from rubiknetic.cube_logic.cubie import SOLVED  # noqa: E402
from rubiknetic.cube_logic.transitions import infer_move  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402
from rubiknetic.cube_physics.rig import AuditedSim, EditAuditError, NumericalFailure, TurnRig  # noqa: E402

name = sys.argv[1]
seq = sys.argv[2] if len(sys.argv) > 2 else "U R U' R' F F'"
m = mujoco.MjModel.from_xml_string(xml_for(name))
sim = AuditedSim(m)
mujoco.mj_forward(m, sim.d)
d = sim.d
ro = CubeReadout(m, 0.019)
mp = M1Params()
rig = TurnRig(sim, pad_close_target=-(mp.pad_open_clearance + mp.grip_overshoot))
dt = m.opt.timestep
try:
    t = time.perf_counter()
    sim.step(int(3.0 / dt))
    rest_sps = int(3.0 / dt) / (time.perf_counter() - t)
except NumericalFailure as e:
    print(f"{name}: REST numerical failure {e}")
    sys.exit()
o = ro.observe(d)
rest_ok = o.valid and o.state == SOLVED
prev = o.cube
oks, errs, t, s0 = [], [], time.perf_counter(), d.time
for mv in parse(seq):
    _, r0 = ro.poses(d)
    mem = ro.layer_members(d, mv.face)
    try:
        rig.turn(mv, record=False)
    except (NumericalFailure, EditAuditError) as e:
        print(f"{name}: {mv} ABORT {e}")
        oks.append(False)
        break
    _, r1 = ro.poses(d)
    ang = float(np.mean(CubeReadout.rotation_about_deg(r0, r1, mem, mv.face)))
    errs.append(ang + 90.0 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns])
    o = ro.observe(d)
    try:
        obs_mv = infer_move(prev, o.cube) if o.valid else None
    except Exception:
        obs_mv = None
    oks.append(o.valid and obs_mv is not None and str(obs_mv) == str(mv))
    if o.valid:
        prev = o.cube
turn_sps = (d.time - s0) / dt / (time.perf_counter() - t)
print(f"{name}: rest valid+solved {rest_ok} ({rest_sps:.0f} steps/s) | turns {sum(oks)}/{len(parse(seq))} match "
      f"| errors {[round(e, 2) for e in errs]} | turn {turn_sps:.0f} steps/s")
