"""D18 step 1 (UNSCORED; G2 pre-registration §7 P-2, P-105 layout): two xArm7 + G2 on one table, facing each other,
cube axis horizontal between them. Arm A grips from the D end (P-04, P-97 stabiliser fingertip, 30 mm over D+E);
arm B (C1 turner fingertip, P-107) grips the U layer 14 mm deep from the U end.

Frames (world): table top z = 0; arm A base at the origin facing +x; arm B base at (L, 0, 0) yawed 180 deg (faces -x).
Cube centre C = (L/2, 0, H). Cube +z (U) = world +x, cube +x = world +y (the pad normal), cube +y = world +z.
Grasp poses: arm A's gripper axis = +x, pad normal (gripper y) = +y; arm B's gripper axis = -x, pad normal +y.
Gripper base positions follow from the fingertip geometry (distal end of the fingertip box; same G2 model):
  A: D face at the stabiliser fingertip's proximal end;  B: fingertip distal end 14 mm inside the U face.
IK: damped least squares on the gripper base pose (position + full orientation), joint limits enforced, several
seeds, best kept. Reports joint angles, margins to limits, residuals, and contacts between robot parts, robot and
table, and robot and cube at the grasp pose (cube placed, grippers closed to 57 mm).
Usage (WSL): python layout.py [--L 1.0] [--H 0.25]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "experiments" / "D17_real_holder_m7"))
import hold as H  # noqa: E402
import turn as TU  # noqa: E402

bm = H.bm
OUT = HERE / "results"


def gripper_frames():
    """Gripper-base-frame z of the fingertips' distal ends (A: P-97, B: C1), from the compiled specs."""
    out = {}
    for tag, tip_half in (("p97", None), ("c1", TU.TURNER_TIP_HALF)):
        m = H.robot_spec(robot_path(), tip_half=tip_half, tag=tag).compile()
        d = mujoco.MjData(m)
        cal = calib()
        d.qpos[[m.jnt_qposadr[m.joint(j).id] for j in bm.GRIPPER_JOINTS]] = cal["theta_at_calib_width_rad"]
        mujoco.mj_kinematics(m, d)
        b = m.body("xarm_gripper_base_link").id
        Rb, pb = d.xmat[b].reshape(3, 3), d.xpos[b]
        g = m.geom(f"left_fingertip_{tag}").id
        out[tag] = float((Rb.T @ (d.geom_xpos[g] - pb))[2] + m.geom_size[g, 2])
    return out


def robot_path() -> Path:
    return bm.OUT_DIR / "xarm7_g2_1305+.xml"


def calib() -> dict:
    return json.loads((bm.OUT_DIR / "xarm7_g2_1305+_gripper_calibration.json").read_text())


def targets(L: float, Hc: float):
    p = H.m7_params()
    half = 1.5 * p.pitch - p.gap / 2
    tips = gripper_frames()
    C = np.array([L / 2, 0.0, Hc])
    ex = np.array([1.0, 0, 0])
    # A: D face (C - half ex) at the fingertip's proximal end (tip - 30 mm along +ex)
    tipA = C - half * ex + 2 * H.TIP_HALF[2] * ex
    pA = tipA - tips["p97"] * ex
    RA = np.column_stack([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]])      # x, y, z of the gripper base
    tipB = C + (half - TU.INSERTION_U) * ex
    pB = tipB + tips["c1"] * ex
    RB = np.column_stack([[0, 0, 1.0], [0, 1.0, 0], [-1.0, 0, 0]])
    return C, half, (pA, RA), (pB, RB), tips


def ik(m, d, body: str, p_t, R_t, seeds, iters: int = 400) -> tuple[np.ndarray, float, float]:
    qa = np.array([m.jnt_qposadr[m.joint(j).id] for j in bm.ARM_JOINTS])
    va = np.array([m.jnt_dofadr[m.joint(j).id] for j in bm.ARM_JOINTS])
    lo, hi = m.jnt_range[[m.joint(j).id for j in bm.ARM_JOINTS]].T
    b = m.body(body).id
    jp, jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
    best = (None, np.inf, np.inf)
    for q0 in seeds:
        d.qpos[:] = 0
        d.qpos[qa] = q0
        for _ in range(iters):
            mujoco.mj_kinematics(m, d)
            mujoco.mj_comPos(m, d)
            R, pcur = d.xmat[b].reshape(3, 3), d.xpos[b]
            ep = p_t - pcur
            er = Rotation.from_matrix(R_t @ R.T).as_rotvec()     # world-frame rotation error (no 180 deg saddle)
            if np.linalg.norm(ep) < 1e-6 and np.linalg.norm(er) < 1e-6:
                break
            mujoco.mj_jacBody(m, d, jp, jr, b)
            J = np.vstack([jp[:, va], jr[:, va]])
            e = np.concatenate([ep, er])
            dq = J.T @ np.linalg.solve(J @ J.T + 1e-4 * np.eye(6), e)
            d.qpos[qa] = np.clip(d.qpos[qa] + 0.5 * dq, lo, hi)
        mujoco.mj_kinematics(m, d)
        R, pcur = d.xmat[b].reshape(3, 3), d.xpos[b]
        ep = float(np.linalg.norm(p_t - pcur))
        er = float(np.degrees(np.arccos(np.clip((np.trace(R.T @ R_t) - 1) / 2, -1, 1))))
        if ep + 0.001 * er < best[1] + 0.001 * best[2]:
            best = (d.qpos[qa].copy(), ep, er)
    return best


SEEDS = [np.array(s) for s in (
    [0, -0.247, 0, 0.909, 0, 1.15644, 0], [0, 0.3, 0, 1.2, 0, 0.9, 0], [0, 0.0, 0, 1.6, 0, 1.6, 0],
    [0, -0.5, 0, 0.8, 0, 1.3, 0], [0, 0.5, 0, 1.8, 0, 1.3, 0], [0, 0.2, 0, 2.2, 0, 2.0, 0])]


ROLL180 = np.diag([-1.0, -1.0, 1.0])     # the same grasp rolled 180 deg about the gripper axis (symmetric fingers)


def best_of(m, d, p_t, R_t):
    cands = [ik(m, d, "xarm_gripper_base_link", p_t, R_t @ Rr, SEEDS) + (k,) for k, Rr in
             enumerate((np.eye(3), ROLL180))]
    return min(cands, key=lambda c: c[1] + 0.001 * c[2] - 0.0001 * margin_of(m, c[0]))


def margin_of(m, q) -> float:
    lo, hi = m.jnt_range[[m.joint(j).id for j in bm.ARM_JOINTS]].T
    return float(np.degrees(np.min(np.minimum(q - lo, hi - q))))


def solve(L: float, Hc: float) -> dict:
    C, half, (pA, RA), (pB, RB), tips = targets(L, Hc)
    m = H.robot_spec(robot_path()).compile()
    d = mujoco.MjData(m)
    qA, eA, rA, kA = best_of(m, d, pA, RA)
    yaw = np.array([[-1.0, 0, 0], [0, -1.0, 0], [0, 0, 1.0]])            # arm B base: yaw 180 deg at (L, 0, 0)
    baseB = np.array([L, 0, 0])
    qB, eB, rB, kB = best_of(m, d, yaw.T @ (pB - baseB), yaw.T @ RB)
    lo, hi = m.jnt_range[[m.joint(j).id for j in bm.ARM_JOINTS]].T
    margin = lambda q: float(np.degrees(np.min(np.minimum(q - lo, hi - q))))  # noqa: E731
    return {"L": L, "H": Hc, "cube_centre": C.tolist(), "half_mm": half * 1e3, "tip_dist_mm": {k: v * 1e3 for k, v in tips.items()},
            "A": {"roll180": bool(kA), "q": qA.tolist(), "pos_err_mm": eA * 1e3, "rot_err_deg": rA, "limit_margin_deg": margin(qA),
                  "gripper_base": pA.tolist()},
            "B": {"roll180": bool(kB), "q": qB.tolist(), "pos_err_mm": eB * 1e3, "rot_err_deg": rB, "limit_margin_deg": margin(qB),
                  "gripper_base": pB.tolist(), "base": baseB.tolist(), "yaw_deg": 180}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=float, nargs="*", default=[0.8, 0.9, 1.0, 1.1])
    ap.add_argument("--H", type=float, nargs="*", default=[0.25, 0.3, 0.35, 0.4, 0.45])
    a = ap.parse_args()
    rows = []
    for L in a.L:
        for Hc in a.H:
            r = solve(L, Hc)
            rows.append(r)
            print(f"L {L:.2f} H {Hc:.2f}: A err {r['A']['pos_err_mm']:.3f} mm {r['A']['rot_err_deg']:.3f} deg margin "
                  f"{r['A']['limit_margin_deg']:.1f} deg | B err {r['B']['pos_err_mm']:.3f} mm {r['B']['rot_err_deg']:.3f} "
                  f"deg margin {r['B']['limit_margin_deg']:.1f} deg", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "layout_ik.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
