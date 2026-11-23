"""ER9 Part G (PROTOCOL.md, Part G, G.3 and G.12): magnet lists of the Part G arms, the arm registry, the MagnetSystem
builder and its installation into ER7's trial code, and self-check GS3. Wrapper only: lists, no force-law code.

Arms (explicit registry; any other name is refused, G.3 "Arm names"):
  L0    M5's 48 corner-edge magnets, 4 x 2 mm N35 (magnets.layout(pitch 19 mm, gap 0.05 mm)); reference / GS1
  C52   the 40 entries of magnets.core_layout(MagnetParams(4 mm, 3 mm, grade), clearance = 2e-4); reference / GS2
  PG8   L0 + the 16 corner entries of core_layout (8 corner pairs: kind "corner" on the piece, "core_corner" on core)
  PG20  L0 + all 40 entries of core_layout (= L0 u C52)
  PG20r PG20 with the moments of the 12 edge PIECE magnets of core_layout (kind "edge", body != "core") reversed,
        so each edge repels its own core magnet. A reversed moment is represented the only way magnets.py represents
        a polarity: the magnet's body-frame direction "dir" is negated (magnets.py: moment = |m| * n, with n = R dir in
        MagnetSystem.world; the near-field term carries s = sign(n1 . n2)).
Every magnet is tagged with its type by magnets.typed (4 x 2 N35 for the 48; 4 x 3 at `grade` for the core pairs), and
the MagnetSystem gets the 4 x 3 table through type_tables (magnets.py, MagnetSystem docstring). `grade` is the core
magnets' grade (default N52, U3; N35 and N42 for P2's rows); it has no effect on L0.

Tables (validated files only; nothing is built here): 4 x 2 N35 = M5's table exactly as M4._tables_for loads it for
ER7's L0 when no TABLES_PROVIDER is set (M4.magnet_availability, then near_field_tables(MP42, M4.TABLES)); any
M4.TABLES_PROVIDER (ER7 sets one for C52) is ignored here, so the 4 x 2 magnets never get another type's table; 4 x 3 N52 = M6's table (hash checked by ER7's m6_table); 4 x 3 N35 / N42 = M6's
table times the exact Br^2 factor, through er9_probe.table_for (Part C's derived files in tables/, checked against
M6's table on every call).

Usage (WSL, repo root):  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_layouts.py gs3
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from rubiknetic.cube_physics import magnets as M
from rubiknetic.cube_physics.m1_model import M1Params

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

ARMS = ("L0", "C52", "PG8", "PG20", "PG20r")
PART_G_ARMS = ("PG8", "PG20", "PG20r")
GRADES = ("N35", "N42", "N52")
GAP = 5e-5                                             # M5 / ER7 piece gap (E5_scored_m5/run.py GAP)
CLEAR = 2e-4                                           # C52 core clearance (er7_run.py CLEAR)
BASE_OVERRIDES = {"radial_preload": 0.0}               # B1 (E4_scored_m4/run.py BASE_OVERRIDES)
PITCH = M1Params(**{**BASE_OVERRIDES, "gap": GAP}).pitch
MP42 = M.MagnetParams()                                # M5: 4 x 2 mm N35, wall 0.4 mm (= E5 magnet_params_for({}))
CORNER_KINDS = ("corner", "core_corner")               # the corner entries of core_layout()

# G.11 "Pair counts on different bodies" (hand count, INFERENCE in the protocol; GS3 checks them).
G11_PAIR_COUNTS = {"L0": {"42-42": 1092, "43-43": 0, "cross": 0, "total": 1092},
                   "C52": {"42-42": 0, "43-43": 590, "cross": 0, "total": 590},
                   "PG8": {"42-42": 1092, "43-43": 92, "cross": 744, "total": 1928},
                   "PG20": {"42-42": 1092, "43-43": 590, "cross": 1872, "total": 3554},
                   "PG20r": {"42-42": 1092, "43-43": 590, "cross": 1872, "total": 3554}}
G3_MAGNET_COUNTS = {"L0": 48, "C52": 40, "PG8": 64, "PG20": 88, "PG20r": 88}


# ---- registry --------------------------------------------------------------------------------------------------------
def check_arm(arm: str, grade: str = "N52") -> None:
    """Refuses any arm outside the explicit registry and any grade outside N35 / N42 / N52."""
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}: the Part G registry is {ARMS} (G.3, arm names)")
    if grade not in GRADES:
        raise ValueError(f"unknown core-magnet grade {grade!r}: allowed {GRADES} (U3)")


def mp43(grade: str = "N52") -> M.MagnetParams:
    """The core-pair magnet type: 4 x 3 mm at `grade` (wall and shared fields at the MagnetParams defaults, as ER7)."""
    check_arm("C52", grade)
    return M.MagnetParams(diameter=0.004, length=0.003, grade=grade)


def has_42(arm: str) -> bool:
    check_arm(arm)
    return arm != "C52"


def has_43(arm: str) -> bool:
    check_arm(arm)
    return arm != "L0"


def system_mp(arm: str, grade: str = "N52") -> M.MagnetParams:
    """The MagnetSystem's primary type (must be the type of at least one magnet): 4 x 2 when the arm has M5's 48,
    else the 4 x 3 type. With one type the system is single-type and bit-identical to ER7's L0 / C52 installation."""
    check_arm(arm, grade)
    return MP42 if has_42(arm) else mp43(grade)


def arm_types(arm: str, grade: str = "N52") -> list[M.MagnetParams]:
    check_arm(arm, grade)
    return ([MP42] if has_42(arm) else []) + ([mp43(grade)] if has_43(arm) else [])


# ---- magnet lists ----------------------------------------------------------------------------------------------------
def base_mags(pitch: float = PITCH, gap: float = GAP) -> list[dict]:
    """M5's 48 (magnets.layout), typed 4 x 2 N35."""
    return M.typed(M.layout(pitch, gap, MP42), MP42)


def core_mags(grade: str = "N52", which: str = "all") -> list[dict]:
    """core_layout(4 x 3 at grade, clearance 2e-4), typed; which = 'all' (40) or 'corner' (the 16 corner entries)."""
    mp = mp43(grade)
    mags = M.core_layout(mp, CLEAR)
    if which == "corner":
        mags = [g for g in mags if g["kind"] in CORNER_KINDS]
    elif which != "all":
        raise ValueError(which)
    return M.typed(mags, mp)


def reversed_edge_piece(mags: list[dict]) -> list[dict]:
    """Copies with the moment of every 4 x 3 edge PIECE magnet reversed (dir negated); others unchanged (copied)."""
    out = []
    for g in mags:
        h = {**g, "pos": np.array(g["pos"], float).copy(), "dir": np.array(g["dir"], float).copy()}
        if is_43(h) and h["kind"] == "edge" and h["body"] != "core":
            h["dir"] = -h["dir"]
        out.append(h)
    return out


def is_43(g: dict) -> bool:
    mp = g.get("mp")
    return mp is not None and (mp.diameter, mp.length) == (0.004, 0.003)


def arm_mags(arm: str, grade: str = "N52", pitch: float = PITCH, gap: float = GAP) -> list[dict]:
    """The arm's typed magnet list, M5's 48 first (if any), then the core_layout entries in core_layout's order."""
    check_arm(arm, grade)
    if arm == "L0":
        return base_mags(pitch, gap)
    if arm == "C52":
        return core_mags(grade)
    if arm == "PG8":
        return base_mags(pitch, gap) + core_mags(grade, "corner")
    if arm == "PG20":
        return base_mags(pitch, gap) + core_mags(grade)
    return reversed_edge_piece(base_mags(pitch, gap) + core_mags(grade))          # PG20r


def pair_counts(mags: list[dict]) -> dict:
    """Pairs on different bodies by type combination (what MagnetSystem evaluates; same-body pairs are skipped)."""
    n = len(mags)
    ii, jj = np.triu_indices(n, 1)
    body = np.array([g["body"] for g in mags])
    keep = body[ii] != body[jj]
    t43 = np.array([is_43(g) for g in mags])
    a, b = t43[ii[keep]], t43[jj[keep]]
    return {"42-42": int(np.sum(~a & ~b)), "43-43": int(np.sum(a & b)), "cross": int(np.sum(a != b)),
            "total": int(keep.sum())}


# ---- tables and the MagnetSystem -------------------------------------------------------------------------------------
def _load(name: str, rel: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


def probe_module():
    """er9_probe (loads ER7's runner, M5's and M4's runners); loaded lazily, only when validated tables are needed."""
    return _load("er9_probe", "experiments/ER9_anchored_core_layouts/er9_probe.py")


def table_files(arm: str, grade: str = "N52") -> dict:
    """{type label: {"file", "sha256"}} of the validated tables the arm uses (for the runner's records)."""
    P = probe_module()
    out = {}
    if has_42(arm):
        info = P.M4.magnet_availability(MP42)            # refuses unless M5's table and V3 record are in place
        out[M.type_label(MP42)] = {"file": info["table_file"], "sha256": info["table_sha256"],
                                   "validated_tilt_deg": info.get("validated_tilt_deg")}
    if has_43(arm):
        mp, path, sha = P.table_for(grade)               # N52: M6's table (hash checked); else exact Br^2 rescaling
        assert mp == mp43(grade), (mp, grade)
        out[M.type_label(mp)] = {"file": str(path.relative_to(REPO)), "sha256": sha}
    return out


def load_tables(arm: str, grade: str = "N52") -> dict:
    """{MagnetParams: near-field splines} for every type of the arm, from the validated files only."""
    check_arm(arm, grade)
    P = probe_module()
    out = {}
    if has_42(arm):
        # M4._tables_for(MP42) without its TABLES_PROVIDER branch (E4_scored_m4/run.py _tables_for): the provider, if
        # set (ER7's C52 setup sets it to the 4x3 N52 table), is deliberately ignored for the 4x2 type.
        P.M4.magnet_availability(MP42)                   # refuses unless M5's table and V3 record are in place
        out[MP42] = M.near_field_tables(MP42, P.M4.TABLES)
    if has_43(arm):
        mp, path, _ = P.table_for(grade)
        assert mp == mp43(grade)
        out[mp] = M.near_field_tables(mp, path.parent)
    return out


def build_system(model, arm: str, grade: str = "N52", tables: dict | None = None, cls=M.MagnetSystem,
                 pitch: float = PITCH, gap: float = GAP) -> M.MagnetSystem:
    """The arm's MagnetSystem on `model` (any M1 model with the cubie and core bodies). tables: {MagnetParams: splines}
    (default: load_tables, validated files only). cls: MagnetSystem or a subclass (M4.RecordingMagnetSystem, or
    er9g_stats.with_class_stats(...) for the per-class diagnostic)."""
    check_arm(arm, grade)
    tables = load_tables(arm, grade) if tables is None else tables
    mp = system_mp(arm, grade)
    others = {t: tables[t] for t in arm_types(arm, grade) if t != mp}
    return cls(model, pitch, gap, mp, tables=tables[mp], mags=arm_mags(arm, grade, pitch, gap),
               type_tables=others or None)


def install_er7(arm: str, grade: str = "N52", cls=None, tables: dict | None = None) -> None:
    """Applies a Part G arm to this (fresh) worker process, the way er9_probe.configure / er9_hybrid.configure apply a
    layout: ER7's run_one then runs every magnet trial with the arm's MagnetSystem.

    What it changes (process globals only; no physics code): M4.use_magnets is replaced by a builder modelled on
    E7.use_core (same compile path M4._compile_paused, same B1 params, same reuse-by-key and install), which builds
    build_system(model, arm, grade, cls=cls or M4.RecordingMagnetSystem). E7.setup_arm is wrapped so the replacement
    survives ER7's own arm setup: with job["er7_arm"] == "C52" ER7 still sets the 20 deg tilt, M4.TABLES_PROVIDER and
    the C52 table record (GS2); with "L0" ER7 changes nothing and M4 records M5's 4 x 2 table check (GS1, Part G arms).
    The wrapper refuses an er7_arm other than "L0" for arms with 4x2 magnets, and other than "C52" for C52.
    The 4 x 3 table of a Part G arm is not in M4's record: the runner adds table_files(arm, grade).
    The `mp` M4 passes (M5's nominal magnet from the job's overrides) is ignored, as E7.use_core ignores it."""
    check_arm(arm, grade)
    P = probe_module()
    E7, M4 = P.E7, P.M4
    from rubiknetic.cube_physics.m1_model import build_m1_xml
    cache: dict = {}

    def use_arm(mp, gap):
        M4.configure_process()
        if mp is None:
            raise RuntimeError("ER9 Part G runs magnet-arm jobs only")
        key = ("ER9G", arm, grade, gap)
        if M4._MS is not None and M4._MS_KEY == key:
            M4._MS.install()
            return M4._MS
        M.MagnetSystem.uninstall()
        M4._MS, M4._MS_KEY = None, None
        p = M1Params(**{**M4.BASE_OVERRIDES, "gap": gap})
        m = M4._compile_paused(build_m1_xml(p))
        if "tables" not in cache:
            cache["tables"] = load_tables(arm, grade) if tables is None else tables
        ms = build_system(m, arm, grade, cache["tables"], cls or M4.RecordingMagnetSystem, p.pitch, p.gap)
        M4._MS, M4._MS_KEY = ms, key
        ms.install()
        return ms

    orig = getattr(E7.setup_arm, "_er9g_orig", E7.setup_arm)

    want = "L0" if has_42(arm) else "C52"

    def setup_arm(er7_arm: str) -> None:
        # An arm with M5's 4x2 magnets runs as ER7 arm L0 only (no TABLES_PROVIDER, M5's table record, M5's tilt);
        # C52-only (GS2) runs as ER7 arm C52 only (ER7's 20 deg tilt and C52 table record).
        if er7_arm != want:
            raise ValueError(f"ER9 Part G arm {arm} must run with er7_arm={want!r}, got {er7_arm!r}")
        orig(er7_arm)
        M4.use_magnets = use_arm

    setup_arm._er9g_orig = orig
    E7.setup_arm = setup_arm
    M4.use_magnets = use_arm


# ---- GS3 -------------------------------------------------------------------------------------------------------------
def _same(a: list[dict], b: list[dict]) -> bool:
    return (len(a) == len(b) and all(x["body"] == y["body"] and np.array_equal(x["pos"], y["pos"])
                                     and np.array_equal(x["dir"], y["dir"]) for x, y in zip(a, b)))


def gs3(grade: str = "N52") -> dict:
    """GS3 (G.5): the registry lists equal the direct lists (bodies, positions, directions exactly), the magnet counts
    are 88 / 64 / 88 (and 48 / 40), the pair counts equal G.11's table, PG20r differs from PG20 in exactly the 12 edge
    piece directions (negated), and the types are tagged as stated."""
    lay = M.layout(PITCH, GAP, MP42)
    core = M.core_layout(mp43(grade), CLEAR)
    corner = [g for g in core if g["kind"] in CORNER_KINDS]
    rev = [{**g, "dir": -g["dir"] if (g["kind"] == "edge" and g["body"] != "core") else g["dir"]} for g in core]
    direct = {"L0": lay, "C52": core, "PG8": lay + corner, "PG20": lay + core, "PG20r": lay + rev}
    out, ok = {}, True
    for arm in ARMS:
        mine = arm_mags(arm, grade)
        types = sorted({M.type_label(g["mp"]) for g in mine})
        want_types = sorted(M.type_label(t) for t in arm_types(arm, grade))
        n42 = sum(not is_43(g) for g in mine)
        row = {"equal_to_direct_list": _same(mine, direct[arm]), "n_magnets": len(mine),
               "n_magnets_expected": G3_MAGNET_COUNTS[arm], "pair_counts": pair_counts(mine),
               "pair_counts_expected": G11_PAIR_COUNTS[arm], "types": types,
               "types_ok": types == want_types and all((g["mp"] == MP42) != is_43(g) for g in mine)
               and n42 == (48 if has_42(arm) else 0)}
        if arm == "PG20r":
            base = arm_mags("PG20", grade)
            flipped = [k for k, (a, b) in enumerate(zip(base, mine)) if not np.array_equal(a["dir"], b["dir"])]
            row["n_reversed"] = len(flipped)
            row["reversed_are_edge_piece_43"] = all(is_43(mine[k]) and mine[k]["kind"] == "edge"
                                                    and mine[k]["body"] != "core"
                                                    and np.array_equal(mine[k]["dir"], -base[k]["dir"])
                                                    for k in flipped)
            row["positions_unchanged"] = all(np.array_equal(a["pos"], b["pos"]) and a["body"] == b["body"]
                                             for a, b in zip(base, mine))
        row["pass"] = bool(row["equal_to_direct_list"] and row["n_magnets"] == row["n_magnets_expected"]
                           and row["pair_counts"] == row["pair_counts_expected"] and row["types_ok"]
                           and (arm != "PG20r" or (row["n_reversed"] == 12 and row["reversed_are_edge_piece_43"]
                                                   and row["positions_unchanged"])))
        ok &= row["pass"]
        out[arm] = row
    return {"grade": grade, "arms": out, "pass": bool(ok)}


if __name__ == "__main__":
    if sys.argv[1:] != ["gs3"]:
        raise SystemExit("usage: er9g_layouts.py gs3")
    print(json.dumps({g: gs3(g) for g in GRADES}, indent=1))
