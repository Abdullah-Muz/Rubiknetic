"""Measure the official UFACTORY Gripper G2 STEP CAD (with / without fingertips).

Run with the CAD tool venv and -I (third-party inputs):
    ~/.venvs/cadtools/bin/python -I experiments/P2_robot_model/measure_g2_step.py

Inputs (git-ignored; see third_party_cad/robot/SOURCES.md):
    third_party_cad/robot/g2_step_derived/g2_with_fingers.glb      (cascadio STEP->GLB, metres)
    third_party_cad/robot/g2_step_derived/g2_without_fingers.glb
Output (git-ignored): third_party_cad/robot/g2_step_derived/step_measurements.json

Method: faces of the with-fingers model farther than TOL from the without-fingers surface are
the parts that the "without fingers" file removes (fingertips and their fasteners). They are
split into connected components and measured. Frame (INFERENCE, checked against the drawing):
  length axis = longest overall extent, opening axis = the other horizontal extent that the two
  removed groups are separated along, origin on the flange plane (extreme of the length axis
  farthest from the fingertips), centred on the overall bounding box in the other two axes.
Mesh tessellation tolerance 0.05 mm linear => dimensions are good to ~0.1 mm, not to the CAD.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
DER = ROOT / "third_party_cad/robot/g2_step_derived"
TOL = 0.3e-3  # m


def load(p: Path) -> trimesh.Trimesh:
    m = trimesh.load(str(p), force="mesh", process=True)
    m.merge_vertices()
    return m


def main() -> int:
    w = load(DER / "g2_with_fingers.glb")
    wo = load(DER / "g2_without_fingers.glb")
    out: dict = {"units": "mm", "tolerance_mm": TOL * 1e3}
    out["with_bbox_mm"] = np.round(w.bounds * 1e3, 2).tolist()
    out["without_bbox_mm"] = np.round(wo.bounds * 1e3, 2).tolist()

    # dense reference point cloud of the without-fingers surface
    pts, _ = trimesh.sample.sample_surface_even(wo, 1_500_000, radius=0.15e-3, seed=0)
    ref = cKDTree(np.vstack([pts, wo.vertices]))
    # a face is "extra" if all three vertices are farther than TOL from the reference surface
    dv = ref.query(w.vertices)[0]
    extra = np.all(dv[w.faces] > TOL, axis=1)
    sub = w.submesh([np.nonzero(extra)[0]], append=True)
    comps = [c for c in sub.split(only_watertight=False) if c.area > 1e-6]  # drop slivers < 1 mm^2
    out["removed_components"] = len(comps)

    ext = w.extents
    ax_len = int(np.argmax(ext))
    cen_all = np.array([c.centroid for c in comps])
    spread = np.ptp(cen_all, axis=0)
    spread[ax_len] = -1
    ax_open = int(np.argmax(spread))
    ax_thk = 3 - ax_len - ax_open
    # flange plane: the extreme of the length axis farthest from the removed parts
    tip_side = np.sign(cen_all[:, ax_len].mean() - w.bounds.mean(axis=0)[ax_len])
    flange = w.bounds[0, ax_len] if tip_side > 0 else w.bounds[1, ax_len]
    origin = w.bounds.mean(axis=0)
    origin[ax_len] = flange

    def to_g(p):
        p = np.atleast_2d(p) - origin
        q = np.stack([p[:, ax_open], p[:, ax_thk], tip_side * p[:, ax_len]], axis=1)
        return q  # (opening, thickness, length-from-flange)

    out["frame"] = {"axes_step_index": {"opening": ax_open, "thickness": ax_thk, "length": ax_len},
                    "note": "x=opening, y=thickness, z=distance from flange plane (mm)"}
    out["overall_extent_mm"] = {"opening": round(ext[ax_open] * 1e3, 2),
                                "thickness": round(ext[ax_thk] * 1e3, 2),
                                "length": round(ext[ax_len] * 1e3, 2)}
    parts = []
    for c in comps:
        g = to_g(c.vertices) * 1e3
        lo, hi = g.min(0), g.max(0)
        e = hi - lo
        parts.append({
            "faces": int(len(c.faces)),
            "bbox_min_mm": np.round(lo, 2).tolist(), "bbox_max_mm": np.round(hi, 2).tolist(),
            "extent_mm": np.round(e, 2).tolist(),
            "volume_mm3": round(float(abs(c.volume)) * 1e9, 1) if c.is_watertight else None,
            "watertight": bool(c.is_watertight),
            "side": "+x" if (lo[0] + hi[0]) > 0 else "-x",
        })
    parts.sort(key=lambda p: (-np.prod(p["extent_mm"]), p["side"]))
    out["removed_parts"] = parts

    # fingertips = the two largest removed parts; fasteners = the rest
    tips = [p for p in parts[:2]]
    if len(tips) == 2:
        lt = min(tips, key=lambda p: p["bbox_min_mm"][0])
        rt = max(tips, key=lambda p: p["bbox_min_mm"][0])
        out["fingertip_inner_gap_mm_bbox"] = round(rt["bbox_min_mm"][0] - lt["bbox_max_mm"][0], 2)
        out["fingertip_outer_span_mm"] = round(rt["bbox_max_mm"][0] - lt["bbox_min_mm"][0], 2)
        out["fingertip_tip_distance_from_flange_mm"] = round(max(lt["bbox_max_mm"][2], rt["bbox_max_mm"][2]), 2)
    # mount patch: without-fingers vertices within 1 mm of any removed part
    tipmesh = trimesh.util.concatenate([c for c in comps])
    near = cKDTree(tipmesh.vertices).query(wo.vertices)[0] < 1.0e-3
    if near.any():
        g = to_g(wo.vertices[near]) * 1e3
        out["mount_patch_points"] = int(near.sum())
        for side, sel in (("-x", g[:, 0] < 0), ("+x", g[:, 0] > 0)):
            if sel.any():
                out[f"mount_contact_bbox_{side}_mm"] = [np.round(g[sel].min(0), 2).tolist(),
                                                        np.round(g[sel].max(0), 2).tolist()]
    (DER / "step_measurements.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
