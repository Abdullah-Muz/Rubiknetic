"""Convert the UFACTORY Gripper G2 COLLADA (.dae) meshes to binary STL for MuJoCo.

Run with the separate CAD tool venv (trimesh + pycollada), NOT the project venv,
and with ``-I`` because the inputs are third-party downloads:

    ~/.venvs/cadtools/bin/python -I experiments/P2_robot_model/convert_g2_meshes.py

Inputs (third-party, BSD-3-Clause, (c) UFACTORY; see third_party_cad/robot/SOURCES.md):
    third_party_cad/robot/src/xarm_ros2/xarm_description/meshes/gripper/xarm/*_g2.dae
Outputs (git-ignored):
    third_party_cad/robot/g2_meshes/*.stl
    third_party_cad/robot/g2_meshes/conversion_report.json

Pipeline check: the same loader is applied to the ORIGINAL-gripper (G1) .dae files and
the result is compared with UFACTORY's own G1 .stl files (same directory). If the
loader got units, axes or node transforms wrong, the G1 comparison fails.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "third_party_cad/robot/src/xarm_ros2/xarm_description/meshes/gripper/xarm"
OUT = ROOT / "third_party_cad/robot/g2_meshes"

PARTS = [
    "base_link",
    "left_outer_knuckle",
    "left_finger",
    "left_inner_knuckle",
    "right_outer_knuckle",
    "right_finger",
    "right_inner_knuckle",
]


def load_dae(path: Path) -> trimesh.Trimesh:
    # force="mesh" concatenates all geometry nodes with their scene-graph transforms
    # applied (Blender cameras/lights in the file carry no geometry).
    mesh = trimesh.load(str(path), force="mesh", process=True)
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        raise RuntimeError(f"no triangle geometry in {path.name}")
    return mesh


def drop_far_fragments(mesh: trimesh.Trimesh, box_m: float = 0.15) -> tuple[trimesh.Trimesh, dict]:
    """Remove connected components not entirely inside a +-box_m cube about the
    part frame (the whole gripper fits in +-0.11 m). base_link_g2.dae contains ~160 zero-area fragments near
    (-250, 473, 100) mm (an export artefact); without this filter the MuJoCo convex
    hull of the gripper body would span half a metre."""
    comps = mesh.split(only_watertight=False)
    keep, drop = [], []
    for c in comps:
        outside = bool(np.any(np.abs(c.bounds) > box_m))  # not entirely inside the box
        (drop if outside else keep).append(c)
    info = {
        "components_total": len(comps),
        "components_dropped": len(drop),
        "faces_dropped": int(sum(len(c.faces) for c in drop)),
        "area_dropped_mm2": float(sum(c.area for c in drop) * 1e6),
    }
    if not drop:
        return mesh, info
    return trimesh.util.concatenate(keep), info


def describe(mesh: trimesh.Trimesh) -> dict:
    return {
        "faces": int(len(mesh.faces)),
        "vertices": int(len(mesh.vertices)),
        "bounds_min_m": [round(float(v), 6) for v in mesh.bounds[0]],
        "bounds_max_m": [round(float(v), 6) for v in mesh.bounds[1]],
        "watertight": bool(mesh.is_watertight),
        "volume_m3": float(mesh.volume) if mesh.is_watertight else None,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "trimesh": trimesh.__version__,
        "python": sys.version.split()[0],
        "g1_pipeline_check": {},
        "g2": {},
    }
    ok = True

    # 1. Pipeline check on G1: dae -> mesh vs UFACTORY's own G1 stl.
    for part in PARTS:
        dae = load_dae(SRC / f"{part}.dae")
        stl = trimesh.load(str(SRC / f"{part}.stl"), force="mesh")
        db = float(np.max(np.abs(dae.bounds - stl.bounds)))
        report["g1_pipeline_check"][part] = {"max_bounds_diff_m": db}
        if db > 5e-4:
            ok = False
        print(f"G1 check {part:22s} max |bounds(dae)-bounds(stl)| = {db*1e3:.3f} mm")

    # 2. Convert G2 (and compare each G2 part with its G1 counterpart).
    from scipy.spatial import cKDTree

    for part in PARTS:
        mesh = load_dae(SRC / f"{part}_g2.dae")
        mesh, frag = drop_far_fragments(mesh)
        out = OUT / f"{part}_g2.stl"
        mesh.export(str(out), file_type="stl")
        info = describe(mesh)
        info["output"] = out.name
        info["fragment_filter"] = frag
        g1 = trimesh.load(str(SRC / f"{part}.stl"), force="mesh")
        haus = max(
            cKDTree(g1.vertices).query(mesh.vertices)[0].max(),
            cKDTree(mesh.vertices).query(g1.vertices)[0].max(),
        )
        info["vertex_hausdorff_to_G1_mm"] = float(haus * 1e3)
        if frag["components_dropped"]:
            print(f"   {part}: dropped {frag['components_dropped']} far fragments "
                  f"({frag['faces_dropped']} faces, {frag['area_dropped_mm2']:.3f} mm^2)")
        print(f"   {part}: vertex Hausdorff distance to the G1 mesh = {haus*1e3:.4f} mm")
        report["g2"][part] = info
        ext = (mesh.bounds[1] - mesh.bounds[0]) * 1e3
        print(
            f"G2 {part:22s} faces={info['faces']:7d} extent_mm=({ext[0]:.1f}, {ext[1]:.1f}, {ext[2]:.1f})"
            f" watertight={info['watertight']}"
        )

    report["g1_pipeline_check_pass"] = ok
    (OUT / "conversion_report.json").write_text(json.dumps(report, indent=2))
    print("G1 pipeline check:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
