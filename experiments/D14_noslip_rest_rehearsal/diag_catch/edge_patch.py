"""Diagnostic geometry swap (UNSCORED, nothing adopted): rounded piece edges instead of the 45 deg chamfer.

`install()` replaces `m1_model._chamfered_box_vertices(h, c)` in the CURRENT process, when the environment variable
DIAG_EDGE_R_MM is set, with a faceted rounded box: same half-size h (so the 0.05 mm piece gap is unchanged), edges and
corners rounded with radius R. Fillet facets at polar/azimuth steps of 30 deg, so the first facet meets each flat face
at 15 deg instead of 45 deg. The repo's model code is not edited.
"""
import os
import numpy as np

STEPS_DEG = (0.0, 30.0, 60.0, 90.0)


def rounded_box_vertices(h: float, R: float) -> np.ndarray:
    assert 0 < R < h
    dirs = set()
    for th in np.radians(STEPS_DEG):
        for ph in np.radians(STEPS_DEG):
            u = (np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th))
            dirs.add(tuple(round(x, 12) for x in u))
    pts = set()
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                s = np.array([sx, sy, sz], float)
                for u in dirs:
                    p = s * (h - R) + R * s * np.array(u)
                    pts.add(tuple(round(x, 12) for x in p))
    return np.array(sorted(pts))


def install() -> float | None:
    r = os.environ.get("DIAG_EDGE_R_MM")
    if not r:
        return None
    R = float(r) / 1000.0
    from rubiknetic.cube_physics import m1_model
    m1_model._chamfered_box_vertices = lambda h, c: rounded_box_vertices(h, R)
    return R
