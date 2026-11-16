"""UNSCORED diagnostic (2026-11-15): time-resolved re-simulation of rehearsal trials, read-only instrumentation.

Usage (WSL, repo root): diag_drift.py <tid> <move_index|rest> [gap_m] [size_tag]
Re-runs the rehearsal job <tid> (seeds 7000-7999, already unscored) through the same M4 runner path, with a monitor
subclass that only READS state. For the target move it logs every 10 steps (5 ms):
  pad force, turning-layer axial speed, per non-target piece: rotation since move start, signed lattice error about
  the turn axis, magnet axial torque (about the core), with each piece classed as middle slice or opposite layer.
For 'rest' it logs every face layer's signed lattice error (D8-0 layer_error) from model creation onward.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path("/mnt/c/Users/abdul/OneDrive/Desktop/Rubiknetic")
OUT = Path("/mnt/c/Users/abdul/AppData/Local/Temp/claude/b6672f8dce1e00f4/3140f1d7-6e9e-4f5a-9e6c-c7e61a5f6350/scratchpad/diag")
tid, target = sys.argv[1], sys.argv[2]
gap = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0001
size = sys.argv[4] if len(sys.argv) > 4 else None

spec = importlib.util.spec_from_file_location("reh", ROOT / "experiments/D8_alignment/rehearsal_gap.py")
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)
R, ST = H.R, H.R.ST
from rubiknetic.cube_physics import scored                                    # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES              # noqa: E402

EVERY = 10


class Diag(R.MagnetMonitor):
    def __init__(self, m, ro):
        super().__init__(m, ro)
        self.k, self.turn_idx, self.rows, self.meta = 0, -1, [], {}
        self.t_start = None
        self.on = False

    def start_trial(self, d):
        super().start_trial(d)
        self.t_start = float(d.time)

    def begin_turn(self, face, members):
        super().begin_turn(face, members)
        self.turn_idx += 1
        self.on = target != "rest" and self.turn_idx == int(target)
        if self.on:
            d = self._d
            pos, self.r0 = self.ro.poses(d)
            self.face, self.axis = face, np.array(FACE_NORMAL[face], float)
            self.nt = [i for i in scored._NONCENTRE if i not in members]
            self.cls = ["slice" if abs(pos[i] @ self.axis) < 0.5 else "opposite" for i in self.nt]
            self.members = list(members)
            self.meta = {"face": face, "nontarget": self.nt, "class": self.cls, "t_begin": float(d.time)}

    def end_turn(self):
        res = super().end_turn()
        if self.on:
            self.meta["t_end"] = float(self._d.time)
            self.on = False
        return res

    def _pad_force(self, d):
        n = d.ncon
        if not n:
            return 0.0
        pads = self.pad_geoms[self.face]
        idx = np.nonzero(np.isin(d.contact.geom1[:n], pads) | np.isin(d.contact.geom2[:n], pads))[0]
        f6, tot = np.zeros(6), 0.0
        for i in idx:
            mujoco.mj_contactForce(self.m, d, int(i), f6)
            tot += f6[0]
        return tot

    def _mag_axial(self, d, idx):
        if R._MS is None or R._MS.last is None:
            return [0.0] * len(idx)
        p, F, T, _ = R._MS.last
        c = d.xpos[self.ro.core]
        tau = (T + np.cross(p - c, F)) @ self.axis
        return [float(tau[R._MS.body == self.ro.body_ids[i]].sum()) for i in idx]

    def __call__(self, d):
        super().__call__(d)
        self.k += 1
        if self.k % EVERY:
            return
        if target == "rest":
            if self.k % 50 == 0:
                e, _ = ST.piece_errors(self.ro, d)
                self.rows.append({"t": float(d.time), **{f: ST.layer_error(self.ro, d, f) for f in FACES},
                                  "piece_err": [[float(x) for x in e[i]] for i in scored._NONCENTRE]})
            return
        if not self.on:
            return
        _, r = self.ro.poses(d)
        e, _ = ST.piece_errors(self.ro, d)
        w = d.cvel[self.ro.body_ids[self.members], :3] @ self.axis
        self.rows.append({
            "t": float(d.time),
            "pad_N": self._pad_force(d),
            "layer_dps": float(np.degrees(np.mean(w))),
            "layer_rot_deg": float(np.mean(self.ro.rotation_about_deg(self.r0, r, self.members, self.face))),
            "layer_mag_Nm": float(sum(self._mag_axial(d, self.members))),
            "nt_rot_deg": [float(x) for x in self.ro.rotation_about_deg(self.r0, r, self.nt, self.face)],
            "nt_err_deg": [float(e[i] @ self.axis) for i in self.nt],
            "nt_mag_Nm": self._mag_axial(d, self.nt),
            "tl_err_deg": [float(e[i] @ self.axis) for i in self.members],
        })


R.configure_process()
scored.Monitor = Diag
job = next(j for j in H.jobs(gap, OUT) if j["tid"] == tid)
R.BASE_OVERRIDES = {"radial_preload": 0.0, "gap": gap}
kw = copy.deepcopy(job["kw"])
if size:
    kw["overrides"]["magnet"] = size
rec, ms, _ = R.run_trial(job["kind"], kw, True)
mon = R.MagnetMonitor.last
OUT.mkdir(parents=True, exist_ok=True)
tag = f"{tid}_{target}_gap{gap * 1e3:g}" + (f"_{size}" if size else "")
summary = {"tid": tid, "target": target, "gap": gap, "size": size, "pass": rec.get("pass"),
           "t_start": mon.t_start, "meta": mon.meta}
if target != "rest":
    summary["per_move"] = {k: v for k, v in rec["per_move"][int(target)].items()
                           if k.startswith(("nontarget", "t_", "turn_error", "ok_", "layer_magnet", "move"))}
else:
    summary["rest_rotation_deg"] = rec["rest_rotation_deg"]
(OUT / f"{tag}.json").write_text(json.dumps({**summary, "rows": mon.rows}))
print(json.dumps(summary, default=str)[:1500])
