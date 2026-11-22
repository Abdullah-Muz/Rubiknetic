"""D12 worker: one job per fresh process (PROTOCOL.md section 10 S3). Called only through `d12_run.py _worker`.

Job kinds:
  * replay  - one E1-2 single-move trial exactly as experiments/ER9_anchored_core_layouts/er9_turn_diag.py replays it
              (setup = draw_setup(seed), Trial (0.5 s settle), rig.turn(move): close, ramp, hold, open, settle), with the
              arm configured as er9_turn_diag.py configures it (ER9's own modules, loaded unchanged), the explicit
              overrides of d12_common.overrides_for applied, and one read-only step hook (section 9). The hook also
              rebuilds er9_turn_diag.py's 20-step samples and er9_catch_diag.py's catch record (S1).
  * stage4  - one guard-rail trial in L0 under R1 through E4's run_trial (E5's patched module, loaded unchanged).
  * s2_l0 / s2_w3 / s1b - model builds only (S2, S1b); no step is taken.
Overrides: M1Params fields go into M4.BASE_OVERRIDES (and the gap also into use_magnets(mp, gap)); setup fields are
replaced after the frozen draw (scored.draw_setup is wrapped in this process only, so the harness functions that draw
their own setup see the same replacement). Nothing else is patched. The hook reads mjData only; scored.AuditedSim
raises EditAuditError if anything wrote the audited state arrays between steps.
"""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import os
import platform
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import d12_common as C  # noqa: E402

ER9_DIAG = REPO / "experiments/ER9_anchored_core_layouts/results/probe/diag"
E17_NONE_REF = REPO / "experiments/E5_scored_m5/results/E1-7/magnet=none__6move.json"
_STATE = {"jobs_in_process": 0, "t_import": time.time()}


# ---- process helpers ------------------------------------------------------------------------------------------------
def _load(name: str, rel: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_er9():
    """ER9's probe module, exactly as er9_turn_diag.py loads it (it loads ER7's runner, which loads E5's and E4's)."""
    return _load("er9_probe", "experiments/ER9_anchored_core_layouts/er9_probe.py")


def machine_state() -> dict:
    out = {"loadavg": None, "mem_available_mb": None, "mem_total_mb": None}
    try:
        out["loadavg"] = list(os.getloadavg())
    except OSError:
        pass
    try:
        with open("/proc/meminfo") as f:
            kv = {ln.split(":")[0]: ln.split(":")[1].strip() for ln in f}
        out["mem_available_mb"] = int(kv["MemAvailable"].split()[0]) / 1024.0
        out["mem_total_mb"] = int(kv["MemTotal"].split()[0]) / 1024.0
    except (OSError, KeyError, ValueError):
        pass
    return out


def peak_rss_mb() -> float | None:
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0     # Linux: kB
    except (ImportError, OSError):
        return None


def versions() -> dict:
    import mujoco
    import scipy
    import rubiknetic
    return {"mujoco": mujoco.__version__, "numpy": np.__version__, "scipy": scipy.__version__,
            "python": platform.python_version(), "platform": platform.platform(),
            "rubiknetic_file": str(Path(rubiknetic.__file__).resolve())}


def configure_layout(P, layout: str) -> dict | None:
    """The arm configuration of er9_turn_diag.py (lines 25-44), for D12's registry only. 'none' is E5's magnet=none
    arm: ER7's L0 setup (a no-op) and no magnet system."""
    C.check_arm(layout)
    E7 = P.E7
    E7.set_seeds(E7.ER7_GLOBALS)
    if layout in ("L0", "none"):
        E7.setup_arm("L0")
        return None
    if layout.startswith("X"):
        cfg = {**P.arms()["W1"], "scale": float(layout[1:]), "variant": f"N35 x {layout[1:]} (ad hoc)"}
    else:
        cfg = P.C52_CFG if layout == "C52" else P.arms()[layout]
    name = C.required_table_name(cfg)
    if name is not None and not (Path(P.TABLES) / name).exists():
        # er9_probe.table_for would write this derived table under ER9's folder; D12 writes only under its results/
        raise C.Refused(f"derived near-field table {Path(P.TABLES) / name} is missing; D12 does not build tables "
                        f"(layout {layout})")
    P.configure(cfg)
    E7.setup_arm("C52")
    return cfg


def apply_m1_overrides(M4, ov: dict) -> dict:
    M4.BASE_OVERRIDES = {**M4.BASE_OVERRIDES, **ov["m1"]}
    return dict(M4.BASE_OVERRIDES)


def wrap_draw_setup(scored, setup_ov: dict):
    """Section 8.1 'draw first, then replace', installed only when a setup field is under test."""
    orig = scored.draw_setup
    if setup_ov:
        def draw_setup(seed, misalign_max_deg=1.0):
            return C.draw_then_replace(orig, seed, setup_ov, misalign_max_deg)
        scored.draw_setup = draw_setup
    return orig


def write_record(path: Path, rec: dict) -> None:
    """Temporary file, then a hard link to the final name (fails if it exists), then the temporary name is removed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = gzip.compress(json.dumps(rec, default=C.jsonable).encode(), 9, mtime=0)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with open(tmp, "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.link(tmp, path)
    except FileExistsError:
        os.unlink(tmp)
        raise
    except OSError:                          # file system without hard links: exclusive create instead
        with open(path, "xb") as f:
            f.write(data)
    os.unlink(tmp)


def read_record(path: Path) -> dict:
    return json.loads(gzip.decompress(Path(path).read_bytes()))


# ---- geometry checks (S2) -------------------------------------------------------------------------------------------
def geometry_check(model, params, xml: str) -> dict:
    """S2: compiled cubie half-size = (pitch - gap) / 2 and compiled mesh vertices = _chamfered_box_vertices(h, chamfer)
    (compiled vertices are float32: tolerance 10 nm), and the XML mesh is that vertex list."""
    import mujoco
    from rubiknetic.cube_logic.geometric import HOME_POSITIONS
    from rubiknetic.cube_physics.m1_model import _chamfered_box_vertices, _fmt, cubie_name
    h = (params.pitch - params.gap) / 2
    want = _chamfered_box_vertices(h, params.chamfer)
    d = mujoco.MjData(model)
    mujoco.mj_kinematics(model, d)
    half, worst, counts = 0.0, 0.0, set()
    for home in HOME_POSITIONS:
        g = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, cubie_name(home) + "_g")
        mid = model.geom_dataid[g]
        v = model.mesh_vert[model.mesh_vertadr[mid]: model.mesh_vertadr[mid] + model.mesh_vertnum[mid]].astype(float)
        rel = d.geom_xpos[g] + v @ d.geom_xmat[g].reshape(3, 3).T - np.array(home, float) * params.pitch
        counts.add(len(rel))
        half = max(half, float(np.abs(rel).max()))
        dmin = np.min(np.linalg.norm(want[:, None, :] - rel[None, :, :], axis=2), axis=1)
        worst = max(worst, float(dmin.max()))
    tol = 1e-8
    return {"h_m": h, "chamfer_m": params.chamfer, "compiled_half_size_m": half,
            "half_size_ok": bool(abs(half - h) <= tol), "vertex_counts": sorted(counts),
            "vertices_max_dev_m": worst, "vertices_ok": bool(worst <= tol and counts == {len(want)}),
            "xml_vertex_ok": f'<mesh name="cubelet" vertex="{_fmt(want)}"/>' in xml, "tolerance_m": tol}


def l0_face_gaps(mags: list[dict], length: float) -> list[float]:
    """Corner-edge face gaps (m) of a corner-edge layout: centre distance of facing magnets minus the magnet length."""
    by_body: dict = {}
    for g in mags:
        by_body.setdefault(g["body"], []).append(g)
    out = []
    for g in mags:
        if g["kind"] != "corner":
            continue
        home = C.home_of(g["body"])
        k = int(np.argmax(np.abs(g["dir"])))
        eh = list(home)
        eh[k] = 0
        ename = "cubie_" + "".join({-1: "n", 0: "0", 1: "p"}[v] for v in eh)
        cand = [e for e in by_body.get(ename, []) if int(np.argmax(np.abs(e["dir"]))) == k
                and np.sign(e["pos"][k]) == np.sign(home[k])]
        if len(cand) != 1:
            raise AssertionError(f"no unique facing edge magnet for {g['body']} axis {k}")
        out.append(float(abs(np.asarray(g["pos"])[k] - np.asarray(cand[0]["pos"])[k]) - length))
    return out


# ---- instrumentation (section 9) ------------------------------------------------------------------------------------
def _qmul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Hamilton product, wxyz; a (4,), b (n, 4)."""
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    return np.stack([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2], axis=1)


def layer_reference(rots_start: np.ndarray, n: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(u, t): t is CubeReadout.rotation_about_deg's reference tangent, u_i = rots_start[i].T @ t."""
    t = np.cross(n, [1.0, 0, 0]) if abs(n[0]) < 0.9 else np.cross(n, [0, 1.0, 0])
    t = t / np.linalg.norm(t)
    return np.einsum("njk,j->nk", rots_start, t), t


def layer_angles_deg(rots_now: np.ndarray, u: np.ndarray, t: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Vectorised CubeReadout.rotation_about_deg (equal to rounding): signed rotation about n of each piece."""
    v = np.einsum("nij,nj->ni", rots_now, u)
    v = v - np.outer(v @ n, n)
    return np.degrees(np.arctan2(np.cross(t, v) @ n, v @ t))


def _rotvec_deg(q: np.ndarray) -> np.ndarray:
    q = np.where(q[:, :1] < 0, -q, q)
    v = q[:, 1:]
    s = np.linalg.norm(v, axis=1)
    ang = 2.0 * np.arctan2(s, q[:, 0])
    with np.errstate(invalid="ignore", divide="ignore"):
        f = np.where(s > 1e-12, ang / np.where(s > 1e-12, s, 1.0), 2.0)
    return np.degrees(v * f[:, None])


class Instrument:
    """Read-only step hook for one rig.turn (all of close, ramp, hold, open and settle)."""

    def __init__(self, tr, mv, ms, ST, layout: str, seed: int, trace: bool):
        import mujoco
        from rubiknetic.cube_logic.geometric import HOME_POSITIONS
        from rubiknetic.cube_logic.notation import FACE_NORMAL
        from rubiknetic.cube_physics.m1_model import cubie_name
        self.mj = mujoco
        m, d, ro = tr.model, tr.sim.d, tr.ro
        self.tr, self.m, self.d, self.ro, self.ST, self.ms = tr, m, d, ro, ST, ms
        self.layout, self.seed, self.mv = layout, seed, mv
        f = self.face = mv.face
        self.sign, self.commanded = C.turn_sign(mv.quarter_turns), C.commanded_deg(mv.quarter_turns)
        self.dt = float(m.opt.timestep)
        self.act = int(tr.rig.act[f][2])
        self.grip_acts = (int(tr.rig.act[f][0]), int(tr.rig.act[f][1]))
        self.qadr = int(tr.rig.hinge_qadr[f])
        self.gain = float(m.actuator_gainprm[self.act, 0])
        self.bias = np.array(m.actuator_biasprm[self.act, :3], float)
        self.axis = np.array(FACE_NORMAL[f], float)
        _, self.rots0 = ro.poses(d)
        self.members = list(ro.layer_members(d, f))
        cidx = HOME_POSITIONS.index(tuple(int(v) for v in FACE_NORMAL[f]))
        self.layer_idx = self.members + [cidx]
        self.layer_arr = np.array(ro.body_ids[self.layer_idx])
        self.member_arr = np.array(ro.body_ids[self.members])
        self.piece_names = [cubie_name(HOME_POSITIONS[i]) for i in self.layer_idx]
        self.cubies = {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)) for h in HOME_POSITIONS}
        self.names = {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)): (cubie_name(h), h)
                      for h in HOME_POSITIONS}
        self.pad_geoms = np.array([mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, f"pad_{f}{s}_g") for s in "ab"])
        self.u, self.t_ref = layer_reference(self.rots0[self.members], self.axis)
        tm = tr.timing
        q = {1: 1, 2: 2, 3: 1}[mv.quarter_turns]
        self.ph = C.phase_steps(tm.turn_s_per_quarter, self.dt, q, tm.close_s, tm.hold_s, tm.open_s, tm.settle_s)
        cs = np.cumsum([self.ph[k] for k in ("close", "turn", "hold", "open", "settle")])
        self.i_hold_end = int(cs[2] - 1)
        self.N = N = int(cs[-1])
        self.bounds = {k: int(v) for k, v in zip(("close", "turn", "hold", "open", "settle"), cs)}
        self.s0 = tr.sim.steps
        self.turner0 = float(np.degrees(d.qpos[self.qadr]))
        self.target0 = float(np.degrees(tr.rig.target[f]))
        z = lambda: np.zeros(N)  # noqa: E731
        self.a = {k: z() for k in ("t", "turner_deg", "target_deg", "torque_Nm", "pd_unclipped_Nm", "layer_rot_deg",
                                   "pen_cc_mm", "pen_pad_mm", "normal_cc_N", "normal_pad_N", "contact_torque_layer_Nm",
                                   "pad_torque_layer_Nm")}
        self.a["layer_error_deg"] = np.full(N, np.nan)
        self.ai = {k: np.zeros(N, int) for k in ("n_cc", "n_pad", "solver_niter", "warnings_total")}
        self.lag = np.zeros((N, len(self.layer_idx)))
        self.tilt = np.zeros((N, len(self.layer_idx)))
        self.tilt_ax = np.zeros((N, len(self.layer_idx), 3))
        self.mag = np.zeros((N, 4)) if ms is not None else None
        self.filled = 0
        self.overflow = 0
        self.prev_raw, self.cum = None, None
        self.first_clip, self.snap_clip = None, None
        self.win_peak, self.snap_win = -1.0, None
        self.best = {"normal": -1.0}          # er9_catch_diag.py's running maximum (also D12's second snapshot)
        self.snap_best = None
        self.samples = []                     # er9_turn_diag.py's 20-step samples
        self.hold = None
        self.trace = trace
        self.digests = [] if trace else None
        self.digest0 = self._digest(d) if trace else None
        self._w = np.zeros(6)

    # -- per step --
    def _digest(self, dd) -> str:
        h = hashlib.blake2b(digest_size=8)
        for arr in (dd.qpos, dd.qvel, dd.actuator_force):
            h.update(np.ascontiguousarray(arr).tobytes())
        return h.hexdigest()

    def _layer_raw(self, dd) -> np.ndarray:
        rc = dd.xmat[self.ro.core].reshape(3, 3)
        R = dd.xmat[self.member_arr].reshape(-1, 3, 3)
        return layer_angles_deg(np.einsum("ji,njk->nik", rc, R), self.u, self.t_ref, self.axis)

    def _pieces(self, dd, turner_deg: float):
        half = np.radians(-turner_deg) / 2.0
        qa = np.concatenate([[np.cos(half)], np.sin(half) * self.axis])
        rv = _rotvec_deg(_qmul(qa, np.array(dd.xquat[self.layer_arr], float)))
        lag = rv @ self.axis
        tv = rv - np.outer(lag, self.axis)
        return lag, np.linalg.norm(tv, axis=1), tv

    def _snapshot(self, dd, k, reason, F6, cc, b1, b2, adv):
        rows = []
        pos = dd.contact.pos
        fr = dd.contact.frame
        dist = dd.contact.dist
        for i in np.nonzero(cc)[0]:
            n1, n2 = self.names[int(b1[i])][0], self.names[int(b2[i])][0]
            nrm = [float(x) for x in fr[i][:3]]
            rows.append({"force_N": float(F6[i, 0]), "body1": n1, "body2": n2,
                         "pos_mm": [float(x) * 1e3 for x in pos[i]], "normal": nrm, "dist_mm": float(dist[i]) * 1e3,
                         "er9_signature": C.er9_signature(n1, n2, nrm, self.axis)})
        rows.sort(key=lambda r: r["force_N"], reverse=True)
        top = rows[:8]
        return {"reason": reason, "step": int(k), "t": float(dd.time), "turner_deg": float(self.a["turner_deg"][k]),
                "turner_adv_deg": float(adv), "torque_Nm": float(self.a["torque_Nm"][k]),
                "summed_cc_normal_N": float(self.a["normal_cc_N"][k]), "n_cc": int(cc.sum()), "top": top,
                "signature": bool(any(r["er9_signature"] for r in top)),
                "pieces": {nm: {"lag_deg": float(self.lag[k, j]), "tilt_deg": float(self.tilt[k, j]),
                                "tilt_axis": [float(x) for x in self.tilt_ax[k, j]]}
                           for j, nm in enumerate(self.piece_names)},
                "max_abs_lag_deg": float(np.abs(self.lag[k]).max()), "max_tilt_deg": float(self.tilt[k].max())}

    def _er9_catch(self, dd, tot, rows):
        """er9_catch_diag.py's update, verbatim (U layer pieces, scipy from_euler)."""
        from scipy.spatial.transform import Rotation
        turner = float(np.degrees(dd.qpos[self.qadr]))
        pieces = {}
        for b, (nm, h) in self.names.items():
            if h[2] != 1:
                continue
            qw, qx, qy, qz = dd.xquat[b]
            rel = Rotation.from_euler("z", -turner, degrees=True) * Rotation.from_quat([qx, qy, qz, qw])
            rv = np.degrees(rel.as_rotvec())
            pieces[nm] = {"lag_about_z_deg": float(rv[2]), "tilt_deg": float(np.hypot(rv[0], rv[1])),
                          "tilt_axis_xy": [float(rv[0]), float(rv[1])]}
        self.best.update(normal=tot, t=float(dd.time), turner_deg=turner, torque=float(dd.actuator_force[self.act]),
                         top=sorted(rows, reverse=True)[:8], n=len(rows), pieces=pieces)

    def __call__(self, dd) -> None:
        k = self.tr.sim.steps - self.s0 - 1
        if k < 0 or k >= self.N:
            self.overflow += 1
            return
        m, mj, a = self.m, self.mj, self.a
        a["t"][k] = dd.time
        th = float(np.degrees(dd.qpos[self.qadr]))
        a["turner_deg"][k] = th
        ctrl = float(dd.ctrl[self.act])
        a["target_deg"][k] = float(np.degrees(ctrl))
        tau = float(dd.actuator_force[self.act])
        a["torque_Nm"][k] = tau
        a["pd_unclipped_Nm"][k] = (self.gain * ctrl + self.bias[0] + self.bias[1] * float(dd.actuator_length[self.act])
                                   + self.bias[2] * float(dd.actuator_velocity[self.act]))
        raw = self._layer_raw(dd)
        if self.prev_raw is None:
            self.cum = raw.copy()
        else:
            self.cum = self.cum + C.wrap180(raw - self.prev_raw)
        self.prev_raw = raw
        a["layer_rot_deg"][k] = float(np.median(self.cum))
        lag, tilt, tv = self._pieces(dd, th)
        self.lag[k], self.tilt[k], self.tilt_ax[k] = lag, tilt, tv
        adv = (th - self.turner0) * self.sign
        lo, hi = C.THRESHOLDS["window_deg"]
        in_win = lo <= adv <= hi
        # contacts: ER9's order and classification (both bodies cubies -> cubie-cubie, else pad)
        ncon = int(dd.ncon)
        n_cc = n_pad = 0
        normal_cc = normal_pad = 0.0
        F6 = np.zeros((ncon, 6))
        cc = np.zeros(ncon, bool)
        b1 = m.geom_bodyid[dd.contact.geom1[:ncon]]
        b2 = m.geom_bodyid[dd.contact.geom2[:ncon]]
        w = self._w
        for i in range(ncon):
            mj.mj_contactForce(m, dd, i, w)
            F6[i] = w
            if b1[i] in self.cubies and b2[i] in self.cubies:
                cc[i] = True
                n_cc += 1
                normal_cc += float(w[0])
            else:
                n_pad += 1
                normal_pad += float(w[0])
        a["normal_cc_N"][k], a["normal_pad_N"][k] = normal_cc, normal_pad
        self.ai["n_cc"][k], self.ai["n_pad"][k] = n_cc, n_pad
        if ncon:
            dist = dd.contact.dist[:ncon]
            a["pen_cc_mm"][k] = max(0.0, -float(dist[cc].min())) * 1e3 if cc.any() else 0.0
            a["pen_pad_mm"][k] = max(0.0, -float(dist[~cc].min())) * 1e3 if (~cc).any() else 0.0
            frames = dd.contact.frame[:ncon].reshape(-1, 3, 3)
            Fw = np.einsum("nji,nj->ni", frames, F6[:, :3])              # force on geom2 (normal: geom1 -> geom2)
            pos = dd.contact.pos[:ncon] - dd.xpos[self.ro.core]
            tq2 = np.cross(pos, Fw) @ self.axis + F6[:, 3] * (frames[:, 0, :] @ self.axis)
            in1, in2 = np.isin(b1, self.layer_arr), np.isin(b2, self.layer_arr)
            on_layer = np.where(in2, tq2, -tq2)
            cross = cc & (in1 ^ in2)
            g1, g2 = dd.contact.geom1[:ncon], dd.contact.geom2[:ncon]
            pad = (~cc) & (in1 | in2) & (np.isin(g1, self.pad_geoms) | np.isin(g2, self.pad_geoms))
            a["contact_torque_layer_Nm"][k] = float(on_layer[cross].sum())
            a["pad_torque_layer_Nm"][k] = float(on_layer[pad].sum())
        self.ai["solver_niter"][k] = int(np.max(dd.solver_niter))
        self.ai["warnings_total"][k] = int(sum(dd.warning[i].number for i in range(len(dd.warning))))
        if self.ms is not None:
            st = self.ms.stats
            self.mag[k] = (st["max_near_tilt_deg"], st["near_perpendicular"], st["clamped_z"], st["max_force_N"])
        every20 = self.tr.sim.steps % C.THRESHOLDS["sample_every_steps"] == 0
        if every20 or in_win:
            a["layer_error_deg"][k] = float(self.ST.layer_error(self.ro, dd, self.face))
        if every20 and self.face == "U":                       # er9_turn_diag.py's sample, verbatim
            self.samples.append({"t": float(dd.time), "torque": float(dd.actuator_force[self.act]),
                                 "turner_deg": float(np.degrees(dd.qpos[self.qadr])),
                                 "layer_err_deg": float(a["layer_error_deg"][k]), "n_cc": n_cc,
                                 "normal_cc_N": normal_cc, "n_pad": n_pad, "normal_pad_N": normal_pad})
        if normal_cc > self.best["normal"]:                     # er9_catch_diag.py's criterion (tot == normal_cc)
            if self.face == "U":
                rows = []
                for i in np.nonzero(cc)[0]:
                    c = dd.contact[int(i)]
                    rows.append((float(F6[i, 0]), self.names[int(b1[i])][0], self.names[int(b2[i])][0],
                                 [float(x) * 1e3 for x in c.pos], [float(x) for x in c.frame[:3]], float(c.dist) * 1e3))
                self._er9_catch(dd, normal_cc, rows)
            else:
                self.best["normal"] = normal_cc
            self.snap_best = self._snapshot(dd, k, "largest summed cubie-cubie normal force", F6, cc, b1, b2, adv)
        if self.first_clip is None and abs(tau) >= C.THRESHOLDS["clip_R1_Nm"]:
            self.first_clip = k
            self.snap_clip = self._snapshot(dd, k, "first step with |tau| >= 0.999 N m", F6, cc, b1, b2, adv)
        if in_win and abs(tau) > self.win_peak:
            self.win_peak = abs(tau)
            if self.first_clip is None:
                self.snap_win = self._snapshot(dd, k, "window peak (no step reached 0.999 N m)", F6, cc, b1, b2, adv)
        if k == self.i_hold_end:
            _, rnow = self.ro.poses(dd)
            rot = self.ro.rotation_about_deg(self.rots0, rnow, self.members, self.face)
            rot_u = rot + 360.0 * np.round((self.cum - rot) / 360.0)
            self.hold = {"t": float(dd.time), "rotation_per_piece_deg": rot_u.tolist(),
                         "rotation_median_deg": float(np.median(rot_u)),
                         "pads_closed": bool(all(dd.ctrl[g] != 0.0 for g in self.grip_acts))}
        if self.trace:
            self.digests.append(self._digest(dd))
        self.filled += 1

    # -- after the turn --
    def finish(self, log, t_start: float, setup, j3: dict) -> dict:
        if self.overflow or self.filled != self.N or len(log.t) != self.N:
            raise RuntimeError(f"step accounting: filled {self.filled}, expected {self.N}, log {len(log.t)}, "
                               f"overflow {self.overflow}")
        a, dt = self.a, self.dt
        tau = a["torque_Nm"]
        turner_adv = (a["turner_deg"] - self.turner0) * self.sign
        layer_adv = a["layer_rot_deg"] * self.sign
        target_adv = (a["target_deg"] - self.target0) * self.sign
        slip_adv = turner_adv - layer_adv
        win = C.window_mask(turner_adv)
        base = C.baseline_Nm(tau, turner_adv)
        imp = C.catch_impulse(tau, win, base if base is not None else 0.0, dt)
        wp = float(np.abs(tau[win]).max()) if win.any() else 0.0
        wk = int(np.nonzero(win)[0][np.argmax(np.abs(tau[win]))]) if win.any() else None
        pk = int(np.argmax(np.abs(tau)))
        stalls = C.stall_intervals(layer_adv, target_adv, win, dt)
        growth = C.pad_slip_growth(slip_adv, stalls)
        ramp = slice(self.bounds["close"], self.bounds["turn"])
        t_arr = a["t"]
        jam = C.jam_check(self.hold["rotation_median_deg"], self.commanded, a["pen_cc_mm"], t_arr, self.hold["t"],
                          j3["fired"], j3["detail"], float(t_arr[-1]))
        snap_a = self.snap_clip if self.snap_clip is not None else self.snap_win
        events = [None if snap_a is None else snap_a["step"], None if self.snap_best is None else self.snap_best["step"],
                  self.first_clip, wk]
        keep = C.stored_steps(self.N, self.s0, win, events, stalls, dt)
        series = {"step": keep.tolist()}
        full = ("t", "turner_deg", "target_deg", "torque_Nm", "pd_unclipped_Nm", "layer_rot_deg")
        for key, arr in a.items():
            vals = arr[keep]
            if key in full:
                series[key] = [float(x) for x in vals]
            else:
                series[key] = [None if np.isnan(x) else float(f"{x:.7g}") for x in vals]
        series["pad_slip_deg"] = [float(f"{x:.7g}") for x in (a["turner_deg"] - self.turner0 - a["layer_rot_deg"])[keep]]
        for key, arr in self.ai.items():
            series[key] = arr[keep].tolist()
        series["pieces"] = self.piece_names
        # per-piece series at 5 / 4 significant digits (record size); snapshots keep full precision
        series["lag_deg"] = [[float(f"{x:.5g}") for x in row] for row in self.lag[keep]]
        series["tilt_deg"] = [[float(f"{x:.5g}") for x in row] for row in self.tilt[keep]]
        series["tilt_vector_deg"] = [[[float(f"{x:.4g}") for x in v] for v in row] for row in self.tilt_ax[keep]]
        if self.mag is not None:
            series["magnet_stats"] = {"keys": ["max_near_tilt_deg", "near_perpendicular", "clamped_z", "max_force_N"],
                                      "values": [[float(f"{x:.7g}") for x in row] for row in self.mag[keep]]}
        out = {
            "dt_s": dt, "n_steps": self.N, "phase_steps": self.ph, "phase_end_index": self.bounds,
            "phases_s": {k: v * dt for k, v in self.ph.items()},
            "turn_start": {"t": float(t_start), "abs_step": int(self.s0), "turner_deg": self.turner0,
                           "target_deg": self.target0, "layer_members": [self.piece_names[i] for i in
                                                                         range(len(self.members))]},
            "face": self.face, "move": str(self.mv), "turn_sign": self.sign, "commanded_deg": self.commanded,
            "peak_abs_torque_Nm": float(np.abs(tau).max()), "turner_deg_at_peak": float(a["turner_deg"][pk]),
            "t_peak_s": float(t_arr[pk]),
            "window": {"turner_adv_deg": list(C.THRESHOLDS["window_deg"]), "n_steps": int(win.sum()),
                       "empty": bool(not win.any())},
            "window_peak_Nm": wp, "window_peak_step": wk, "baseline_Nm": base, "baseline_missing": base is None,
            "catch_impulse_Nms": imp,
            "fraction_of_steps_at_R1_clip": float(np.mean(np.abs(tau) >= C.THRESHOLDS["clip_R1_Nm"])),
            "fraction_of_ramp_steps_at_R1_clip": float(np.mean(np.abs(tau[ramp]) >= C.THRESHOLDS["clip_R1_Nm"])),
            "first_step_abs_tau_ge_0999": self.first_clip,
            "max_abs_pd_unclipped_Nm": float(np.abs(a["pd_unclipped_Nm"]).max()),
            "stall_intervals": [[int(x), int(y)] for x, y in stalls],
            "stall_intervals_s": [[float(t_arr[x]), float(t_arr[y])] for x, y in stalls],
            "pad_slip_growth_in_stall_deg": growth,
            "max_pen_cc_mm": float(a["pen_cc_mm"].max()), "max_pen_pad_mm": float(a["pen_pad_mm"].max()),
            "hold_end": self.hold, "jam": jam,
            "snapshot_catch": snap_a, "snapshot_max_normal": self.snap_best,
            "solver_niter_max": int(self.ai["solver_niter"].max()),
            "warnings": {str(i): int(self.d.warning[i].number) for i in range(len(self.d.warning))},
            "series": series,
        }
        if self.trace:
            out["trace"] = {"what": "blake2b-64 of (qpos, qvel, actuator_force) after each step", "turn_start":
                            self.digest0, "steps": self.digests}
        if self.face == "U":
            tq = np.abs(np.array(log.turner_torque))
            kk = int(np.argmax(tq))
            out["er9_compat"] = {
                "turn": {"arm": self.layout, "seed": self.seed, "grip_force_N": getattr(setup, "grip_force", None),
                         "turn_s_per_quarter": self.tr.timing.turn_s_per_quarter, "peak_torque_Nm": float(tq.max()),
                         "t_peak_from_start_s": float(log.t[kk] - t_start),
                         "turner_deg_at_peak": float(log.turner_angle_deg[kk]),
                         "fraction_of_steps_at_clip": float(np.mean(tq >= 0.999)),
                         "final_layer_err_deg": float(self.ST.layer_error(self.ro, self.d, "U")),
                         "samples": self.samples},
                "catch": {"arm": self.layout, "seed": self.seed, **self.best}}
        return out


# ---- jobs ---------------------------------------------------------------------------------------------------------
def _base(job: dict) -> dict:
    return {"d12": "D12 turning-stall diagnostic (unscored, exploratory, diagnostic only; PROTOCOL.md)",
            "job_id": job["job_id"], "job": job, "commit": job.get("commit"), "thresholds": C.THRESHOLDS,
            "thresholds_sha256": C.THRESHOLDS_SHA, "machine_start": machine_state(),
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def run_replay(job: dict) -> dict:
    C.check_seed(job["seed"], "replay", job["move"])
    C.check_arm(job["layout"])
    rec = _base(job)
    t0 = time.perf_counter()
    P = load_er9()
    E7, M4, R = P.E7, P.M4, P.R
    scored, ST = E7.scored, M4.ST
    import mujoco
    from rubiknetic.cube_logic import SOLVED, InconsistentTransition, infer_move, parse
    ov = C.overrides_for(job["setting"], job["rig"])             # recomputed here; the job's copy went through JSON
    assert C._norm(ov) == C._norm(job["overrides"]), "job overrides differ from the protocol's"
    cfg = configure_layout(P, job["layout"])
    base_ov = apply_m1_overrides(M4, ov)
    mp = None if job["layout"] == "none" else R.magnet_params_for({})
    ms = M4.use_magnets(mp, ov["gap"])
    if ms is not None:
        ms.reset_neighbour_list()
        ms.reset_stats()
    orig_draw = wrap_draw_setup(scored, ov["setup"])
    drawn = orig_draw(job["seed"])
    setup = scored.draw_setup(job["seed"])
    params = scored.params_for(setup)
    if job["layout"] == "none" and (ms is not None or mujoco.get_mjcb_passive() is not None):
        raise C.Refused("layout 'none' with a magnet system or passive callback installed")
    tr = scored.Trial(params, setup)
    m, d, ro = tr.model, tr.sim.d, tr.ro
    rec.update({
        "notes": [
            "Per-piece lag/tilt and the layer rotation are computed in the step hook from d.xmat / d.xquat, which after "
            "mj_step still hold the pre-step kinematics, while the turner angle is the post-step qpos (method inherited "
            "from ER9's er9_catch_diag.py; kept so that S1 reproduces its records). Lag and pad slip therefore carry a "
            "bias of up to omega * dt (about 0.08 deg at the peak ramp speed at 0.5 ms).",
            "R5's final layer error, drift and settling are not read (section 4).",
        ],
        "layout": job["layout"], "layout_config": cfg, "rig": ov["rig_label"], "rig_name": job["rig"],
        "setting": job["setting"], "overrides_applied": ov, "base_overrides": base_ov,
        "magnet_callback_installed": mujoco.get_mjcb_passive() is not None,
        "magnets": None if ms is None else ms.describe(), "magnet_layout_gap_m": ov["gap"] if ms is not None else None,
        "params": {k: v for k, v in asdict(params).items() if k != "extra"},
        "compiled": {"timestep": float(m.opt.timestep), "turn_forcerange": [float(x) for x in
                     m.actuator_forcerange[tr.rig.act[job['move'][0]][2]]],
                     "cubie_half_size_m": (params.pitch - params.gap) / 2},
        "setup_drawn": asdict(drawn), "setup_used": asdict(setup), "setup_log": tr.sim.setup_log,
        "t0_solved": bool(tr.t0_obs.valid and tr.t0_obs.state == SOLVED),
        "seed": job["seed"], "move": job["move"], "timing": asdict(tr.timing),
    })
    mv = parse(job["move"])[0]
    inst = Instrument(tr, mv, ms, ST, job["layout"], job["seed"], job["trace"])
    tr.sim.hooks.append(inst)
    t_start = d.time
    log = tr.rig.turn(mv, tr.timing)
    obs = ro.observe(d)
    expected = SOLVED.apply(mv)
    observed, inf_err = None, None
    if tr.t0_obs.valid and obs.valid:
        try:
            observed = infer_move(tr.t0_obs.cube, obs.cube)
        except InconsistentTransition as e:
            inf_err = str(e)
    fired = (not rec["t0_solved"]) or (not obs.valid) or obs.state != expected
    j3 = {"fired": bool(fired), "detail": {"observed_valid": bool(obs.valid), "observed_move":
                                           None if observed is None else str(observed), "inference_error": inf_err,
                                           "matches_oracle": bool(obs.valid and obs.state == expected)}}
    rec.update(inst.finish(log, t_start, setup, j3))
    rec["final_layer_err_deg"] = float(ST.layer_error(ro, d, mv.face))
    rec["final_layer_err_read"] = job["rig"] == "R1"        # section 4: R5's final error is not read
    rec["magnet_stats"] = None if ms is None else dict(ms.stats)
    rec["validity"] = C.validity(job["layout"], ov["gap"], rec["magnet_stats"])
    cls = C.catch_class(rec["window_peak_Nm"], rec["baseline_Nm"], bool(rec["stall_intervals"]), job["rig"],
                        rec["jam"]["jam"])
    flags = {"censored_R5": bool(job["rig"] == "R5" and rec["peak_abs_torque_Nm"] >= C.THRESHOLDS["censored_R5_Nm"]),
             "pad_limited": bool(rec["pad_slip_growth_in_stall_deg"] > C.THRESHOLDS["pad_slip_growth_deg"]),
             "above_warning": bool(rec["window_peak_Nm"] >= C.THRESHOLDS["warning_Nm"]),
             "above_realism_reference": bool(rec["window_peak_Nm"] >= C.THRESHOLDS["realism_Nm"])}
    sc = rec["snapshot_catch"]
    rec["max_abs_lag_at_catch_deg"] = None if sc is None else sc["max_abs_lag_deg"]
    rec["max_tilt_at_catch_deg"] = None if sc is None else sc["max_tilt_deg"]
    rec.update({"class": cls["class"], "class_detail": cls, "flags": flags,
                "integrity": {"edit_audit_violations": tr.sim.violations,
                              "numerical_failures": tr.sim.numerical_failures},
                "wall_replay_s": time.perf_counter() - t0})
    return rec


def run_stage4(job: dict) -> dict:
    C.stage4_seed_check(job)
    rec = _base(job)
    t0 = time.perf_counter()
    R = _load("e5_scored_m5_run", "experiments/E5_scored_m5/run.py")
    M4 = R.M4
    scored = R.scored
    ov = C.overrides_for(job["setting"], "R1")
    assert C._norm(ov) == C._norm(job["overrides"]), "job overrides differ from the protocol's"
    base_ov = apply_m1_overrides(M4, ov)
    wrap_draw_setup(scored, ov["setup"])
    kw = {**job["kw"], "overrides": {"gap": ov["gap"]}}
    trial, ms, info = M4.run_trial(job["trial_kind"], kw, True)
    v = {}
    if job["trial_kind"] == "seq":
        from rubiknetic.cube_logic import parse
        v = C.seq_guard_rail([pm["nontarget_drift_deg"] for pm in trial.get("per_move", [])],
                             len(parse(job["kw"]["moves"])), "aborted" in trial)
    elif job["trial_kind"] == "rest":
        r = trial.get("rest_rotation_deg")
        v = {"rest_rotation_deg": r, "pass": bool(r is not None and r <= 0.5 and "aborted" not in trial)}
    else:
        e = trial.get("U_err_after_1s_deg")
        v = {"U_err_after_1s_deg": e, "pass": bool(e is not None and abs(e) <= 0.5 and "aborted" not in trial)}
    rec.update({"layout": "L0", "rig": C.RIGS["R1"]["label"], "rig_name": "R1", "setting": job["setting"],
                "overrides_applied": ov, "base_overrides": base_ov, "trial": trial, "guard_rail": v,
                "validity": C.validity("L0", ov["gap"], trial.get("magnet_stats")),
                "harness_pass_info": trial.get("pass"), "magnet_info": info,
                "wall_replay_s": time.perf_counter() - t0, "sim_time_s": trial.get("sim_time_s")})
    return rec


def run_s2_l0(job: dict) -> dict:
    rec = _base(job)
    P = load_er9()
    M4, R, scored = P.M4, P.R, P.E7.scored
    import mujoco
    from rubiknetic.cube_physics.m1_model import build_m1_xml
    st = C.setting(2.5e-4, 0.0020)
    ov = C.overrides_for(st, "R1")
    configure_layout(P, "L0")
    apply_m1_overrides(M4, ov)
    ms = M4.use_magnets(R.magnet_params_for({}), ov["gap"])
    params = scored.params_for(scored.draw_setup(16100))
    xml = build_m1_xml(params)
    model = mujoco.MjModel.from_xml_string(xml)
    geo = geometry_check(model, params, xml)
    fg = l0_face_gaps(ms.mags, ms.mp.length)
    want = ov["gap"] + 2 * ms.mp.wall
    rec.update({"setting": st, "params_gap": params.gap, "params_chamfer": params.chamfer, "geometry": geo,
                "l0_face_gaps_m": sorted(set(round(x, 15) for x in fg)), "l0_face_gap_expected_m": want,
                "l0_face_gap_ok": bool(len(fg) == 24 and max(abs(x - want) for x in fg) <= 1e-12),
                "magnet_layout_gap_m": ov["gap"]})
    rec["pass"] = bool(params.gap == 2.5e-4 and params.chamfer == 0.0020 and geo["half_size_ok"]
                       and geo["vertices_ok"] and geo["xml_vertex_ok"] and rec["l0_face_gap_ok"])
    return rec


def run_s2_w3(job: dict) -> dict:
    rec = _base(job)
    P = load_er9()
    M4, R = P.M4, P.R
    configure_layout(P, "W3")
    mp = R.magnet_params_for({})
    apply_m1_overrides(M4, C.overrides_for(C.NOMINAL, "R1"))
    p1 = np.array(M4.use_magnets(mp, 5e-5).p_loc, float)
    apply_m1_overrides(M4, C.overrides_for(C.setting(2.5e-4, 0.0020), "R1"))
    ms2 = M4.use_magnets(mp, 2.5e-4)
    p2 = np.array(ms2.p_loc, float)
    rec.update({"n_magnets": int(ms2.n), "w3_magnet_positions_change_with_piece_gap": bool(not np.array_equal(p1, p2)),
                "max_position_change_m": float(np.abs(p1 - p2).max()),
                "note": "ER7's use_core places the layout with E7.core_layout(MP, CLEAR) (no gap argument); the piece "
                        "gap reaches only the model build", "pass": True})
    return rec


def run_s1b(job: dict) -> dict:
    rec = _base(job)
    P = load_er9()
    M4, scored = P.M4, P.E7.scored
    import mujoco
    from rubiknetic.cube_physics.m1_model import build_m1_xml
    ov = C.overrides_for(C.NOMINAL, "R1")
    configure_layout(P, "none")
    apply_m1_overrides(M4, ov)
    ms = M4.use_magnets(None, ov["gap"])
    cb0 = mujoco.get_mjcb_passive()
    params = scored.params_for(scored.draw_setup(16100))
    mujoco.MjModel.from_xml_string(build_m1_xml(params))
    cb1 = mujoco.get_mjcb_passive()
    ref = json.loads(E17_NONE_REF.read_text())["params"]
    diffs = C.params_diffs(ref, {k: v for k, v in asdict(params).items() if k != "extra"}, set(), ("grip_force",))
    rec.update({"magnet_system": ms is None, "callback_before_build": cb0 is not None,
                "callback_after_build": cb1 is not None, "params_diffs_vs_E5_magnet_none": diffs,
                "reference": str(E17_NONE_REF.relative_to(REPO))})
    rec["pass"] = bool(ms is None and cb0 is None and cb1 is None and not diffs)
    return rec


REFUSED_EXIT = 3
KINDS = {"replay": run_replay, "stage4": run_stage4, "s2_l0": run_s2_l0, "s2_w3": run_s2_w3, "s1b": run_s1b}


def worker_main(job: dict, out_path: Path) -> int:
    """Runs one job in this process and writes its record (or a crash record with the traceback)."""
    if _STATE["jobs_in_process"]:
        raise RuntimeError("S3: a D12 worker process runs exactly one job")
    probs = C.frozen_problems(job.get("commit"))
    if probs:                    # refusal, not a crash: no record is written, so the job is not marked as done
        print("REFUSED: code may differ from the job's commit:\n" + "\n".join(probs), file=sys.stderr, flush=True)
        return REFUSED_EXIT
    _STATE["jobs_in_process"] += 1
    try:
        rec = KINDS[job["kind"]](job)
        rec["crash"] = False
    except Exception as e:  # noqa: BLE001  (a crash is recorded with its traceback, never retried silently)
        if isinstance(e, C.Refused) or type(e).__name__ == "Refused":   # D12's or E4's (missing magnet table)
            print(f"REFUSED: {e}", file=sys.stderr, flush=True)          # a precondition: refuse, write nothing
            return REFUSED_EXIT
        rec = {**_base(job), "crash": True, "error": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()}
    rec["process"] = {"pid": os.getpid(), "jobs_in_process": _STATE["jobs_in_process"], "peak_rss_mb": peak_rss_mb(),
                      "wall_process_s": time.time() - _STATE["t_import"]}
    try:
        rec["versions"] = versions()
    except Exception as e:  # noqa: BLE001
        rec["versions"] = {"error": repr(e)}
    rec["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    write_record(out_path, rec)
    return 0 if not rec["crash"] else 1
