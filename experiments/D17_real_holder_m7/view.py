"""Watch D17 stage B in the MuJoCo viewer (visual aid only; nothing is recorded or scored).

Builds the same scene as turn.py (xArm7 + G2 arm A holding the free-core M7 cube by D+E; a second G2 with C1
fingertips on the compliant mount turning U) and plays a move sequence in MuJoCo's interactive viewer.
The simulation runs at about 0.2-0.4x real time on one core, so the motion looks slow.

Usage (WSL, needs a display, e.g. WSLg on Windows 11):
  ~/.venvs/rubiknetic/bin/python experiments/D17_real_holder_m7/view.py [--seq "U U' U2 U' U"] [--grip 20]
      [--turner c1|c2] [--ax-mm 0] [--lat-mm 0] [--dry-run]
Viewer: left-drag rotate, right-drag move, scroll zoom, double-click a body to select it; Space pauses.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import turn as TU  # noqa: E402

from rubiknetic.cube_logic import parse  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", default="U U' U2 U' U")
    ap.add_argument("--grip", type=float, default=20.0)
    ap.add_argument("--turner", default="c1", choices=("c1", "c2"))
    ap.add_argument("--ax-mm", type=float, default=0.0)
    ap.add_argument("--lat-mm", type=float, default=0.0)
    ap.add_argument("--dry-run", action="store_true", help="build the scene and stop before opening the viewer")
    a = ap.parse_args()
    TU.H.TIP_SOLREF = (0.01, 1.0)                     # soft pads, as scored (P-105)
    bm = TU.bm
    robot_path = bm.OUT_DIR / "xarm7_g2_1305+.xml"
    calib = json.loads((bm.OUT_DIR / "xarm7_g2_1305+_gripper_calibration.json").read_text())
    print("building the scene (arm A closes on the cube; about 30 s) ...", flush=True)
    r = TU.Run(robot_path, calib, a.grip, 0.8, TU.K_LIN, a.turner, a.ax_mm / 1e3, a.lat_mm / 1e3)
    print(f"scene ready: nq {r.m.nq}, cube held by arm A at {a.grip:g} N", flush=True)
    if a.dry_run:
        return
    import mujoco.viewer
    with mujoco.viewer.launch_passive(r.m, r.d) as v:
        v.cam.lookat[:] = r.d.xpos[r.core]
        v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.45, 135, -15
        every = max(1, int(round(1 / 60 / r.m.opt.timestep)))
        k = [0]

        def hook(_d):
            k[0] += 1
            if k[0] % every == 0:
                if not v.is_running():
                    raise SystemExit(0)
                v.sync()
        r.sim.hooks.append(hook)
        v.sync()
        for mv in parse(a.seq):
            print(f"move {mv} ...", flush=True)
            res = r.move(mv)
            ok = res["turn_error_deg"]
            print(f"  turn error {ok:+.2f} deg, drift {res['nontarget_drift_deg']:.2f} deg, "
                  f"torque {res['max_roll_torque_Nm']:.3f} N.m", flush=True)
        print("sequence done; close the viewer window to exit", flush=True)
        while v.is_running():
            v.sync()
            time.sleep(0.05)


if __name__ == "__main__":
    main()
