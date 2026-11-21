"""Shared helpers for the ER9 real-piece fit check. Measurement only; all lengths in mm.
The CAD mesh is read from the repo's git-ignored third_party_cad folder and is never written anywhere.
"""
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

GLB = Path("/mnt/c/dev/Rubiknetic/third_party_cad/Assembled_Rubiks_Cube.glb")
HERE = Path(__file__).resolve().parent

_d = np.array([[0.3713, 0.5571, 0.7428], [-0.6247, 0.2343, 0.7449], [0.1826, -0.9129, 0.3651],
               [0.8018, 0.5345, -0.2673], [-0.4767, -0.5720, -0.6674], [0.6882, -0.3441, 0.6390],
               [-0.2132, 0.8528, -0.4767]])
DIRS = _d / np.linalg.norm(_d, axis=1)[:, None]


def load_parts():
    """List of dicts: name, kind (edge/corner/centre/core), home (sign triple), V (mm), F. Stickers are skipped."""
    s = trimesh.load(GLB)
    out = []
    for g in s.dump(concatenate=False):
        name = g.metadata.get("name", "?")
        if "Surface" in name:
            continue
        g = g.copy()
        g.merge_vertices()
        V = np.asarray(g.vertices, float) * 1e3
        F = np.asarray(g.faces, int)
        T = V[F]
        area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
        F = F[area > 1e-12]
        c = (V.min(0) + V.max(0)) / 2
        kind = ("edge" if name.startswith("Edge Square") else "corner" if name.startswith("Corner Square")
                else "centre" if name.startswith("Middle Square") else "core" if name.startswith("Center Part")
                else "other")
        home = tuple(int(x) for x in np.sign(np.round(c / 10.0)))
        out.append({"name": name, "kind": kind, "home": home, "V": V, "F": F})
    return out


def perp_basis(u):
    u = np.asarray(u, float)
    a = np.cross(u, [1.0, 0, 0]) if abs(u[0]) < 0.9 else np.cross(u, [0, 1.0, 0])
    a /= np.linalg.norm(a)
    return a, np.cross(u, a)


def sample_tris(V, F, h, centre=None, radius=None):
    """Points on the surface with spacing <= h along every triangle edge direction (barycentric grid), optionally
    only within `radius` of `centre`."""
    T = V[F]
    if centre is not None:
        cen = T.mean(1)
        rad = np.linalg.norm(T - cen[:, None], axis=2).max(1)
        T = T[np.linalg.norm(cen - centre, axis=1) <= radius + rad]
    if not len(T):
        return np.zeros((0, 3))
    e = np.stack([np.linalg.norm(T[:, 1] - T[:, 0], axis=1), np.linalg.norm(T[:, 2] - T[:, 1], axis=1),
                  np.linalg.norm(T[:, 0] - T[:, 2], axis=1)], 1).max(1)
    n = np.maximum(1, np.ceil(e / h).astype(int))
    pts = []
    for nn in np.unique(n):
        Tn = T[n == nn]
        i, j = np.meshgrid(np.arange(nn + 1), np.arange(nn + 1), indexing="ij")
        m = (i + j) <= nn
        b1 = i[m] / nn
        b2 = j[m] / nn
        b0 = 1 - b1 - b2
        ck = max(1, 200000 // len(b0))                   # at most about 200k points per block (keeps memory small)
        for k0 in range(0, len(Tn), ck):
            Tk = Tn[k0:k0 + ck]
            P = (b0[None, :, None] * Tk[:, None, 0] + b1[None, :, None] * Tk[:, None, 1]
                 + b2[None, :, None] * Tk[:, None, 2]).reshape(-1, 3)
            if centre is not None:
                P = P[np.linalg.norm(P - centre, axis=1) <= radius]
            pts.append(P)
    return np.concatenate(pts) if pts else np.zeros((0, 3))


def sample_tris_rows(V, F, h, centre=None, radius=None):
    """Surface points with guaranteed coverage and no oversampling of thin triangles: rows parallel to each
    triangle's longest edge, at most h apart, with points at most h apart along every row. Every surface point is
    then within 0.71 h of a sample. (sample_tris gives the same guarantee but puts (longest edge / h)^2 / 2 points on
    every triangle, which is far too many on long thin ones.)"""
    T = V[F]
    if centre is not None:
        cen = T.mean(1)
        rad = np.linalg.norm(T - cen[:, None], axis=2).max(1)
        T = T[np.linalg.norm(cen - centre, axis=1) <= radius + rad]
    if not len(T):
        return np.zeros((0, 3))
    E = np.stack([np.linalg.norm(T[:, 1] - T[:, 0], axis=1), np.linalg.norm(T[:, 2] - T[:, 1], axis=1),
                  np.linalg.norm(T[:, 0] - T[:, 2], axis=1)], 1)
    k = E.argmax(1)                                      # longest edge: (k, k+1), apex k+2
    idx = np.arange(len(T))
    A, B, C = T[idx, k], T[idx, (k + 1) % 3], T[idx, (k + 2) % 3]
    c = E[idx, k]
    area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
    hgt = 2 * area / c
    m = np.maximum(1, np.ceil(hgt / h).astype(int))      # rows 0..m
    tri = np.repeat(idx, m + 1)
    first = np.cumsum(m + 1) - (m + 1)
    r = np.arange(len(tri)) - np.repeat(first, m + 1)
    f = r / m[tri]
    start = A[tri] + f[:, None] * (C[tri] - A[tri])
    end = B[tri] + f[:, None] * (C[tri] - B[tri])
    kk = np.maximum(1, np.ceil(c[tri] * (1 - f) / h).astype(int))
    pts = []
    blk = 20000
    for r0 in range(0, len(tri), blk):
        kb = kk[r0:r0 + blk]
        row = np.repeat(np.arange(len(kb)), kb + 1)
        fst = np.cumsum(kb + 1) - (kb + 1)
        j = np.arange(len(row)) - np.repeat(fst, kb + 1)
        g = (j / kb[row])[:, None]
        P = start[r0:r0 + blk][row] * (1 - g) + end[r0:r0 + blk][row] * g
        if centre is not None:
            P = P[np.linalg.norm(P - centre, axis=1) <= radius]
        pts.append(P)
    return np.concatenate(pts) if pts else np.zeros((0, 3))


def _crossings(V, F, P, d, chunk=4096):
    """For every point in P, the number of triangles hit by the ray P + t d, t > 0 (2D projection along d)."""
    a, b = perp_basis(d)
    T = V[F]
    T2 = np.stack([T @ a, T @ b], -1)                    # (F,3,2)
    Tz = T @ d                                           # (F,3)
    P2 = np.stack([P @ a, P @ b], -1)
    Pz = P @ d
    lo, hi = P2.min(0), P2.max(0)
    keep = ((T2[:, :, 0].max(1) >= lo[0]) & (T2[:, :, 0].min(1) <= hi[0]) &
            (T2[:, :, 1].max(1) >= lo[1]) & (T2[:, :, 1].min(1) <= hi[1]) & (Tz.max(1) >= Pz.min()))
    T2, Tz = T2[keep], Tz[keep]
    cnt = np.zeros(len(P), int)
    ts = [[] for _ in range(len(P))] if len(P) <= 8 else None
    if not len(T2):
        return cnt, ts
    A, B, C = T2[:, 0], T2[:, 1], T2[:, 2]
    den = (B[:, 0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (B[:, 1] - A[:, 1]) * (C[:, 0] - A[:, 0])
    ok = np.abs(den) > 1e-14
    A, B, C, Tz, den = A[ok], B[ok], C[ok], Tz[ok], den[ok]
    step = max(1, chunk * 256 // max(1, len(A)))
    for k0 in range(0, len(P), step):
        p = P2[k0:k0 + step]
        px = p[:, 0][:, None]
        py = p[:, 1][:, None]
        w1 = ((px - A[None, :, 0]) * (C[None, :, 1] - A[None, :, 1]) - (py - A[None, :, 1]) * (C[None, :, 0] - A[None, :, 0])) / den
        w2 = ((B[None, :, 0] - A[None, :, 0]) * (py - A[None, :, 1]) - (B[None, :, 1] - A[None, :, 1]) * (px - A[None, :, 0])) / den
        w0 = 1 - w1 - w2
        z = w0 * Tz[None, :, 0] + w1 * Tz[None, :, 1] + w2 * Tz[None, :, 2]
        hit = (w0 >= 0) & (w1 >= 0) & (w2 >= 0) & (z > Pz[k0:k0 + step][:, None] + 1e-9)
        cnt[k0:k0 + step] = hit.sum(1)
        if ts is not None:
            for r in range(hit.shape[0]):
                ts[k0 + r] = sorted((z[r][hit[r]] - Pz[k0 + r]).tolist())
    return cnt, ts


def inside(V, F, P, ndir=5):
    """Majority vote of ray parity over ndir directions. Returns (inside bool array, fraction of points for which the
    directions did not all agree)."""
    P = np.atleast_2d(np.asarray(P, float))
    votes = np.zeros(len(P), int)
    for d in DIRS[:ndir]:
        cnt, _ = _crossings(V, F, P, d)
        votes += cnt % 2
    ins = votes * 2 > ndir
    disagree = float(np.mean((votes != 0) & (votes != ndir))) if len(P) else 0.0
    return ins, disagree


def ray_hits(V, F, origin, d):
    """Sorted distances along origin + t d (t > 0) where the ray crosses the mesh; near-duplicates merged."""
    _, ts = _crossings(V, F, np.asarray(origin, float)[None], np.asarray(d, float))
    out = []
    for t in ts[0]:
        if not out or t - out[-1] > 1e-6:
            out.append(t)
    return out


def cyl_coords(P, c, v):
    q = P - c
    t = q @ v
    rho = np.linalg.norm(q - t[:, None] * v[None], axis=1)
    return t, rho


def cyl_sdf(t, rho, a, hl):
    """Signed distance from points with cylinder coordinates (t along the axis from the centre, rho) to the solid
    cylinder of radius a and half length hl: negative inside."""
    dr = rho - a
    dz = np.abs(t) - hl
    out = np.sqrt(np.maximum(dr, 0) ** 2 + np.maximum(dz, 0) ** 2)
    return np.where((dr <= 0) & (dz <= 0), np.maximum(dr, dz), out)


def cyl_surface_points(c, v, a, hl, h=0.1):
    a1, b1 = perp_basis(v)
    nphi = max(12, int(np.ceil(2 * np.pi * a / h)))
    nz = max(2, int(np.ceil(2 * hl / h)) + 1)
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    ring = np.cos(phi)[:, None] * a1[None] + np.sin(phi)[:, None] * b1[None]
    pts = [c + z * v + a * ring for z in np.linspace(-hl, hl, nz)]
    for r in np.linspace(0, a, max(2, int(np.ceil(a / h)) + 1))[:-1]:
        k = max(1, int(np.ceil(2 * np.pi * r / h)))
        ph = np.linspace(0, 2 * np.pi, k, endpoint=False)
        rr = r * (np.cos(ph)[:, None] * a1[None] + np.sin(ph)[:, None] * b1[None])
        pts.append(c + hl * v + rr)
        pts.append(c - hl * v + rr)
    return np.concatenate(pts)


def cyl_volume_points(c, v, a, hl, h=0.2):
    a1, b1 = perp_basis(v)
    g = np.arange(-a, a + 1e-9, h)
    X, Y = np.meshgrid(g, g, indexing="ij")
    m = X ** 2 + Y ** 2 <= a ** 2
    xy = X[m][:, None] * a1[None] + Y[m][:, None] * b1[None]
    zs = np.linspace(-hl, hl, max(2, int(np.ceil(2 * hl / h)) + 1))
    return np.concatenate([c + z * v + xy for z in zs])


def cyl_cyl_gap(c1, v1, a1, hl1, c2, v2, a2, hl2, h=0.05):
    """Smallest distance between two solid cylinders (negative = overlap depth measure), by dense surface sampling
    of each against the other's exact signed distance."""
    best = np.inf
    for (ca, va, aa, ha, cb, vb, ab, hb) in ((c1, v1, a1, hl1, c2, v2, a2, hl2), (c2, v2, a2, hl2, c1, v1, a1, hl1)):
        P = np.concatenate([cyl_surface_points(ca, va, aa, ha, h), ca[None]])
        t, rho = cyl_coords(P, cb, vb)
        best = min(best, float(cyl_sdf(t, rho, ab, hb).min()))
    return best


def fit_cylinder(V, F, S, c, v, a, hl, tree=None, detail=True):
    """Fit of the solid cylinder (centre c, axis v, radius a, half length hl) in the closed surface (V, F), using the
    dense surface samples S near it.
    wall_mm > 0: fully inside, smallest distance from the cylinder to the surface.
    Otherwise the cylinder is cut by the surface or lies outside: protrusion_mm is the largest distance of a cylinder
    point lying outside the material from the surface, outside_fraction the share of the cylinder volume outside."""
    t, rho = cyl_coords(S, c, v)
    sd = cyl_sdf(t, rho, a, hl)
    c_in = bool(inside(V, F, c[None], ndir=7)[0][0])
    res = {"centre_inside": c_in, "surface_to_cylinder_min_mm": float(sd.min()) if len(sd) else None}
    cut = len(sd) and sd.min() <= 0
    if c_in and not cut:
        res["fully_inside"] = True
        res["wall_mm"] = float(sd.min())
        lat = (np.abs(t) <= hl)
        inner = (rho <= a) & (t < -hl)
        outer = (rho <= a) & (t > hl)
        res["wall_lateral_mm"] = float((rho[lat] - a).min()) if lat.any() else None
        res["wall_inner_face_mm"] = float((-t[inner] - hl).min()) if inner.any() else None
        res["wall_outer_face_mm"] = float((t[outer] - hl).min()) if outer.any() else None
        res["protrusion_mm"] = 0.0
        res["outside_fraction"] = 0.0
        return res
    res["fully_inside"] = False
    if detail:
        Pv = cyl_volume_points(c, v, a, hl, 0.2)
        ins, dis = inside(V, F, Pv, ndir=5)
        res["outside_fraction"] = float(1 - ins.mean())
        res["parity_disagreement"] = dis
        Ps = cyl_surface_points(c, v, a, hl, 0.1)
        ins_s, _ = inside(V, F, Ps, ndir=5)
        if tree is None:
            tree = cKDTree(S)
        if (~ins_s).any():
            d, _ = tree.query(Ps[~ins_s])
            res["protrusion_mm"] = float(d.max())
        else:
            res["protrusion_mm"] = 0.0
    return res


def max_radius(S, c_face, v, L, w):
    """Largest radius of a cylinder on the axis (through c_face along v) spanning t in [0, L] from c_face, such that
    every surface sample is at least w away. Returns the radius (may be <= 0). Does not test that the axis is inside."""
    t, rho = cyl_coords(S, c_face, v)
    dz = np.maximum(np.maximum(-t, t - L), 0.0)
    m = dz < w if w > 0 else dz <= 0
    if not m.any():
        return np.inf
    return float((rho[m] - np.sqrt(np.maximum(w * w - dz[m] ** 2, 0.0))).min())
