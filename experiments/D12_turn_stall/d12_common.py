"""D12 turning-stall diagnostic: pure logic shared by d12_run.py, d12_replay.py and d12_analyze.py (PROTOCOL.md).

Nothing here imports MuJoCo or builds a model. It holds, as frozen constants, what PROTOCOL.md fixes:
  * the seed lists of section 6 and the seed guard (S5): only those seeds; 10000-10999 and 17000-17999 always refused;
  * the arm registry of section 10 S1 (none, L0, W3 for the stages; X0.003, W1, C52 for S1 only);
  * the grid of section 7.1, the one-factor checks of section 7.2 and the rigs R1 / R5 of section 4, as explicit
    overrides ("draw first, then replace", section 8.1);
  * the window, baseline, thresholds and class rules of section 5 (frozen from Stage 1, section 5 "Freeze");
  * the stop-rule arithmetic of section 12.
Unscored, exploratory and diagnostic only. No function here changes a frozen parameter: overrides are returned as
explicit dicts that the replay applies and records.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import replace
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]

# ---- provenance: everything a D12 computation executes or reproduces (section 12: never from uncommitted code) ------
FROZEN_PATHS = [
    "experiments/D12_turn_stall/PROTOCOL.md", "experiments/D12_turn_stall/d12_run.py",
    "experiments/D12_turn_stall/d12_common.py", "experiments/D12_turn_stall/d12_replay.py",
    "experiments/D12_turn_stall/d12_analyze.py", "experiments/D12_turn_stall/d12_stage0.py",
    "src",                                   # whole package: m1_model, rig, scored, readout, magnets (force law), ...
    "pyproject.toml", "uv.lock",
    "experiments/ER9_anchored_core_layouts/er9_probe.py", "experiments/ER9_anchored_core_layouts/er9_layout.py",
    "experiments/ER9_anchored_core_layouts/er9_turn_diag.py", "experiments/ER9_anchored_core_layouts/er9_catch_diag.py",
    "experiments/ER9_anchored_core_layouts/results/screen.json",
    "experiments/ER9_anchored_core_layouts/results/probe/diag",
    "experiments/ER7_core_magnet_rehearsal/er7_run.py", "experiments/E5_scored_m5/run.py",
    "experiments/E4_scored_m4/run.py", "experiments/E1_scored/run.py", "experiments/D8_alignment/d8_1b_stage1.py",
    "experiments/D8_alignment/magnets.py", "experiments/D8_alignment/results/d8_1b_checks*.json",
    "experiments/D10_m5_rest_diagnostic/d10_rest.py",
    "experiments/M6_core_magnets/results/m6_checks.json", "experiments/E5_scored_m5/results/E1-7",
]


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["git", "-c", "core.filemode=false", "-c", "safe.directory=*", "-C", str(REPO), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def frozen_problems(commit: str | None) -> list[str]:
    """Why code may have changed since `commit`: uncommitted changes in FROZEN_PATHS, or a difference in FROZEN_PATHS
    between `commit` and HEAD (`git diff --quiet`, so a commit elsewhere, e.g. Stage 0's output, is allowed)."""
    if not commit:
        return ["no commit recorded"]
    out = []
    dirty = git("status", "--porcelain", "--", *FROZEN_PATHS).stdout.strip()
    if dirty:
        out.append("uncommitted changes in frozen paths:\n" + dirty)
    d = git("diff", "--quiet", commit, "HEAD", "--", *FROZEN_PATHS, check=False)
    if d.returncode == 1:
        names = git("diff", "--name-only", commit, "HEAD", "--", *FROZEN_PATHS, check=False).stdout.strip()
        out.append(f"frozen paths differ between {commit[:12]} and HEAD:\n{names}")
    elif d.returncode != 0:
        out.append(f"git diff {commit[:12]} HEAD failed: {d.stderr.strip()}")
    return out

# ---- section 6: seeds ---------------------------------------------------------------------------------------------
GRID_SEEDS = (16100, 16101, 16900)                       # U; 16100/16101 = ER7 E1-2 U seeds; 16900 fresh
NOMINAL_EXTRA_SEEDS = (16901, 16902)                     # U; fresh
NOMINAL_SEEDS = GRID_SEEDS + NOMINAL_EXTRA_SEEDS
STAGE3_R5 = ((16102, "U'"), (16104, "R"), (16108, "F"), (16903, "U"), (16904, "U"))
STAGE4_SEQ_SEEDS = (16910, 16911)                        # fresh; E1-7's move strings
STAGE4_REST_SEEDS = (16000, 16003)                       # ER7 E1-1 seeds
STAGE4_SNAP_SEED = 16568                                 # ER7 E1-5s range
STAGE4_SNAP_DELTAS = (8.0, -8.0)
SEQUENCES = {"6move": "U U' R R' F F'", "sexy6": " ".join(["R U R' U'"] * 6)}   # E1-7's strings (E1 SEXY6.strip())

REPLAY_SEED_MOVE = {**{s: "U" for s in NOMINAL_SEEDS}, **dict(STAGE3_R5)}
SEED_USES = {
    "replay": frozenset(REPLAY_SEED_MOVE),
    "seq": frozenset(STAGE4_SEQ_SEEDS),
    "rest": frozenset(STAGE4_REST_SEEDS),
    "snap": frozenset({STAGE4_SNAP_SEED}),
}
ALLOWED_SEEDS = frozenset().union(*SEED_USES.values())
FORBIDDEN_RANGES = ((10000, 10999), (17000, 17999))     # E5's scored range (incl. E1-7's 10000); held-out block
RESERVED_BLOCK = (16900, 16999)                          # D12's fresh draws (section 6 "Reserved block")


class Refused(ValueError):
    """A seed, arm or setting the protocol does not allow. The runner stops; nothing is simulated."""


def check_seed(seed, use: str | None = None, move: str | None = None) -> int:
    """S5: refuse 10000-10999 and 17000-17999 always, then any seed outside section 6's list, then a seed used for
    another purpose or with another move than section 6 assigns. Returns the seed."""
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise Refused(f"seed {seed!r} is not an integer")
    seed = int(seed)
    for lo, hi in FORBIDDEN_RANGES:
        if lo <= seed <= hi:
            raise Refused(f"seed {seed} lies in the forbidden range {lo}-{hi} (PROTOCOL section 6, 'Never used')")
    if seed not in ALLOWED_SEEDS:
        raise Refused(f"seed {seed} is not in PROTOCOL section 6's list")
    if use is not None:
        if use not in SEED_USES:
            raise Refused(f"unknown seed use {use!r}")
        if seed not in SEED_USES[use]:
            raise Refused(f"seed {seed} is not a section 6 seed for use {use!r}")
    if move is not None and use == "replay" and REPLAY_SEED_MOVE[seed] != move:
        raise Refused(f"seed {seed} is assigned move {REPLAY_SEED_MOVE[seed]!r}, not {move!r} (section 6)")
    return seed


# ---- section 10 S1: arm registry ------------------------------------------------------------------------------------
STAGE_LAYOUTS = ("none", "L0", "W3")
S1_ONLY_ARMS = ("X0.003", "W1", "C52")                  # registered only to reproduce ER9's turn_* files
REGISTRY = STAGE_LAYOUTS + S1_ONLY_ARMS
CANDIDATE_LAYOUTS = ("none", "L0")                       # W3 is diagnosis only (section 8.2)


def check_arm(name: str, stage_use: bool = False) -> str:
    if name not in REGISTRY:
        raise Refused(f"arm {name!r} is not in D12's registry {REGISTRY} (review G7)")
    if stage_use and name not in STAGE_LAYOUTS:
        raise Refused(f"arm {name!r} is registered for self-check S1 only")
    return name


# ---- sections 4, 7.1, 7.2: rigs, grid, checks -----------------------------------------------------------------------
NOMINAL_GAP = 5e-5            # B1/M5 piece gap 0.05 mm (= E5 run.GAP)
NOMINAL_CHAMFER = 0.0014      # = M1Params().chamfer
GAPS = (5e-5, 1e-4, 2.5e-4)
CHAMFERS = (0.0010, 0.0014, 0.0020)
WALL = 0.0004                 # MagnetParams().wall: L0 face gap = piece gap + 2 * wall
RIGS = {
    "R1": {"turn_torque_limit": 1.0, "label": "R1-frozen (turn_torque_limit 1.0 N·m)"},
    "R5": {"turn_torque_limit": 5.0, "label": "R5-diagnostic (turn_torque_limit 5.0 N·m; NOT the frozen rig)"},
}
CHECKS = {   # section 7.2: one setting changed from the point; M1Params fields only, never the global override
    "a": {"label": "timestep 0.25 ms", "m1": {"timestep": 0.00025}, "setup": {}},
    "b": {"label": "timestep 0.25 ms + cubie solref (0.5 ms, 1)",
          "m1": {"timestep": 0.00025, "cubie_solref": (0.0005, 1.0)}, "setup": {}},
    "c": {"label": "flat cubie solimp (0.99, 0.99, 0.5 mm)", "m1": {"cubie_solimp": (0.99, 0.99, 0.0005)}, "setup": {}},
    "d": {"label": "cubie friction 0.1", "m1": {"cubie_friction": (0.1, 0.0025, 0.0005)}, "setup": {}},
    "e": {"label": "cubie friction 0.5", "m1": {"cubie_friction": (0.5, 0.0025, 0.0005)}, "setup": {}},
    "f": {"label": "setup misalignment 0", "m1": {}, "setup": {"misalign_zero": True}},
    "g": {"label": "grip 10 N", "m1": {}, "setup": {"grip_force": 10.0}},
    "h": {"label": "grip 50 N", "m1": {}, "setup": {"grip_force": 50.0}},
}
SETUP_FIELDS = ("seed", "misalign_deg", "grip_force", "turn_s_per_quarter")


def setting(gap: float = NOMINAL_GAP, chamfer: float = NOMINAL_CHAMFER, check: str | None = None) -> dict:
    if not any(gap == g for g in GAPS):
        raise Refused(f"gap {gap} m is not a section 7.1 level {GAPS}")
    if not any(chamfer == c for c in CHAMFERS):
        raise Refused(f"chamfer {chamfer} m is not a section 7.1 level {CHAMFERS}")
    if check is not None and check not in CHECKS:
        raise Refused(f"check {check!r} is not a section 7.2 check")
    return {"gap": float(gap), "chamfer": float(chamfer), "check": check}


NOMINAL = setting()


def is_nominal(st: dict) -> bool:
    return st["gap"] == NOMINAL_GAP and st["chamfer"] == NOMINAL_CHAMFER and st["check"] is None


def setting_tag(st: dict) -> str:
    t = f"g{round(st['gap'] * 1e3, 6):g}_c{round(st['chamfer'] * 1e3, 6):g}"
    return t + (f"_{st['check']}" if st["check"] else "")


def overrides_for(st: dict, rig: str) -> dict:
    """The explicit overrides of one replay (section 8.1). 'm1': M1Params fields merged into M4.BASE_OVERRIDES
    (which already holds radial_preload 0 and gap 0.05 mm); 'gap': also passed to use_magnets(mp, gap);
    'setup': replacements applied after draw_setup(seed, 1.0). At the nominal point under R1 the only key is
    'gap' = 0.05 mm, the value BASE_OVERRIDES already has, so the frozen model is unchanged."""
    if rig not in RIGS:
        raise Refused(f"rig {rig!r} is not R1 or R5")
    st = setting(st["gap"], st["chamfer"], st["check"])
    m1 = {"gap": st["gap"]}
    if st["chamfer"] != NOMINAL_CHAMFER:
        m1["chamfer"] = st["chamfer"]
    setup = {}
    if st["check"]:
        m1.update(CHECKS[st["check"]]["m1"])
        setup.update(CHECKS[st["check"]]["setup"])
    if rig == "R5":
        m1["turn_torque_limit"] = RIGS["R5"]["turn_torque_limit"]   # R5 differs from R1 in this field only
    return {"m1": m1, "gap": st["gap"], "setup": setup, "rig": rig, "rig_label": RIGS[rig]["label"]}


def fields_under_test(st: dict, rig: str) -> dict:
    """{'m1': M1Params fields changed from the frozen point, 'setup': setup fields replaced} (for S6)."""
    ov = overrides_for(st, rig)
    m1 = {k for k in ov["m1"] if not (k == "gap" and ov["m1"][k] == NOMINAL_GAP)}
    setup = set()
    if ov["setup"].get("misalign_zero"):
        setup.add("misalign_deg")
    if "grip_force" in ov["setup"]:
        setup.add("grip_force")
    return {"m1": m1, "setup": setup}


def draw_then_replace(draw_fn, seed: int, setup_ov: dict, misalign_max_deg: float = 1.0):
    """Section 8.1: draw exactly as the frozen trial does (six misalignments, grip, turn time), THEN replace only the
    field under test. draw_fn is scored.draw_setup (the original, unpatched function)."""
    s = draw_fn(seed, misalign_max_deg)
    unknown = set(setup_ov) - {"misalign_zero", "grip_force"}
    if unknown:
        raise Refused(f"unknown setup overrides {unknown}")
    if setup_ov.get("misalign_zero"):
        s = replace(s, misalign_deg={f: 0.0 for f in s.misalign_deg})
    if "grip_force" in setup_ov:
        s = replace(s, grip_force=float(setup_ov["grip_force"]))
    return s


def s6_diffs(nominal_setup: dict, override_setup: dict, under_test: set) -> list[str]:
    """S6: every setup field not under test equals the nominal replay's field for the same seed (exact)."""
    out = []
    for k in SETUP_FIELDS:
        if k in under_test:
            continue
        if nominal_setup.get(k) != override_setup.get(k):
            out.append(f"setup.{k}: {nominal_setup.get(k)!r} != {override_setup.get(k)!r}")
    return out


def params_diffs(nominal_params: dict, params: dict, under_test: set, ignore=("grip_force",)) -> list[str]:
    """Compiled M1Params fields not under test must equal the nominal replay's (grip_force is seed-drawn)."""
    out = []
    for k in sorted(set(nominal_params) | set(params)):
        if k in under_test or k in ignore:
            continue
        a, b = nominal_params.get(k), params.get(k)
        if _norm(a) != _norm(b):
            out.append(f"params.{k}: {a!r} != {b!r}")
    return out


def _norm(x):
    return json.loads(json.dumps(x, default=list))


# ---- job identity ---------------------------------------------------------------------------------------------------
def replay_job(stage: str, layout: str, st: dict, rig: str, seed: int, trace: bool | None = None,
               purpose: str | None = None) -> dict:
    """One single-move E1-2 replay (section 7.1 'Replay'). trace: per-step state digests for S4 (default: on for the
    nominal point on seed 16100, the S4 pairs). purpose: a job-id suffix for a replay that must run in its own process
    even though an identical replay exists (the timing test re-times; its records stay out of the stage analysis)."""
    check_arm(layout)
    if layout in S1_ONLY_ARMS and not (is_nominal(st) and rig == "R1" and seed == 16100):
        raise Refused(f"arm {layout} is registered for S1 only (nominal, R1, seed 16100)")
    seed = check_seed(seed, "replay")
    st = setting(st["gap"], st["chamfer"], st["check"])
    ov = overrides_for(st, rig)
    if trace is None:
        trace = bool(is_nominal(st) and seed == 16100)
    jid = f"{layout}__{setting_tag(st)}__{rig}__s{seed}" + (f"__{purpose}" if purpose else "")
    return {"kind": "replay", "job_id": jid, "stage": stage, "layout": layout, "setting": st, "rig": rig,
            "seed": seed, "move": REPLAY_SEED_MOVE[seed], "overrides": ov, "trace": bool(trace), "purpose": purpose}


def stage4_job(st: dict, trial: str, seed: int, extra: str | None = None) -> dict:
    """One Stage 4 guard-rail trial in L0 under R1 (section 7.4). trial: '6move' | 'sexy6' | 'rest' | 'snap'."""
    st = setting(st["gap"], st["chamfer"], st["check"])
    if trial in SEQUENCES:
        seed = check_seed(seed, "seq")
        kw = {"moves": SEQUENCES[trial], "seed": seed}
        kind = "seq"
    elif trial == "rest":
        seed = check_seed(seed, "rest")
        kw, kind = {"seed": seed}, "rest"
    elif trial == "snap":
        seed = check_seed(seed, "snap")
        delta = float(extra)
        if delta not in STAGE4_SNAP_DELTAS:
            raise Refused(f"snap delta {delta} is not +8 / -8")
        kw, kind = {"delta_deg": delta, "seed": seed}, "snap"
    else:
        raise Refused(f"unknown Stage 4 trial {trial!r}")
    ov = overrides_for(st, "R1")
    tag = trial if trial != "snap" else f"snap{float(extra):+g}"
    jid = f"S4__L0__{setting_tag(st)}__R1__{tag}__s{seed}"
    return {"kind": "stage4", "job_id": jid, "stage": "stage4", "layout": "L0", "setting": st, "rig": "R1",
            "trial": trial, "trial_kind": kind, "kw": kw, "seed": seed, "overrides": ov}


# ---- section 7: job lists -------------------------------------------------------------------------------------------
def stage1_jobs() -> list[dict]:
    """81 grid R5 + 6 nominal R5 + 15 nominal R1 = 102 (section 7.1)."""
    js = []
    for layout in STAGE_LAYOUTS:
        for g in GAPS:
            for c in CHAMFERS:
                for s in GRID_SEEDS:
                    js.append(replay_job("stage1", layout, setting(g, c), "R5", s))
        for s in NOMINAL_EXTRA_SEEDS:
            js.append(replay_job("stage1", layout, NOMINAL, "R5", s))
        for s in NOMINAL_SEEDS:
            js.append(replay_job("stage1", layout, NOMINAL, "R1", s))
    return js


def stage2_jobs(p_none: dict | None) -> list[dict]:
    """8 checks x 3 grid seeds at P-none (if any) and at P-W3 (section 7.2)."""
    pts = ([("none", p_none)] if p_none is not None else []) + [("W3", NOMINAL)]
    return [replay_job("stage2", lay, setting(p["gap"], p["chamfer"], chk), "R5", s)
            for lay, p in pts for chk in CHECKS for s in GRID_SEEDS]


def stage3_jobs(candidates: list[tuple[str, dict]]) -> list[dict]:
    """Per candidate (layout, setting): R5 on the Stage 3 seeds, R1 on the grid seeds (section 7.3)."""
    js = []
    for lay, st in candidates:
        if lay not in CANDIDATE_LAYOUTS:
            raise Refused(f"layout {lay} can never yield a candidate (section 8.2)")
        js += [replay_job("stage3", lay, st, "R5", s) for s, _ in STAGE3_R5]
        js += [replay_job("stage3", lay, st, "R1", s) for s in GRID_SEEDS]
    return js


def stage4_jobs(settings: list[dict]) -> list[dict]:
    """8 trials per passing setting in L0 under R1, plus 8 for the paired frozen nominal (section 7.4)."""
    out, seen = [], set()
    for st in [NOMINAL] + list(settings):
        for seed in STAGE4_SEQ_SEEDS:
            for name in SEQUENCES:
                out.append(stage4_job(st, name, seed))
        for seed in STAGE4_REST_SEEDS:
            out.append(stage4_job(st, "rest", seed))
        for d in STAGE4_SNAP_DELTAS:
            out.append(stage4_job(st, "snap", STAGE4_SNAP_SEED, d))
    uniq = []
    for j in out:
        if j["job_id"] not in seen:
            seen.add(j["job_id"])
            uniq.append(j)
    return uniq


def selfcheck_replays() -> list[dict]:
    """S1 (5 arms, R1, nominal, 16100) + S4 (R1 and R5 at the nominal point on 16100 for none, L0, W3)."""
    js = [replay_job("selfcheck", a, NOMINAL, "R1", 16100) for a in ("W3", "L0", "X0.003", "W1", "C52", "none")]
    js += [replay_job("selfcheck", a, NOMINAL, "R5", 16100) for a in STAGE_LAYOUTS]
    return js


def timing_replays() -> list[dict]:
    """Section 12 timing test: the S1 replays W3, L0, X0.003 (R1), one no-magnet replay under R1 and one under R5,
    and one L0 replay at 0.25 ms under R5 (all at the nominal point on 16100). Each has its own job id (suffix
    '__timing'), so it is re-timed in its own process rather than reusing a self-check replay's wall time."""
    t = dict(trace=False, purpose="timing")
    return [replay_job("timing", "W3", NOMINAL, "R1", 16100, **t), replay_job("timing", "L0", NOMINAL, "R1", 16100, **t),
            replay_job("timing", "X0.003", NOMINAL, "R1", 16100, **t),
            replay_job("timing", "none", NOMINAL, "R1", 16100, **t),
            replay_job("timing", "none", NOMINAL, "R5", 16100, **t),
            replay_job("timing", "L0", setting(check="a"), "R5", 16100, **t)]


# ---- section 5: classes (frozen from Stage 1) ------------------------------------------------------------------------
THRESHOLDS = {
    "window_deg": (3.0, 15.0), "baseline_deg": (20.0, 70.0),
    "high_R5_Nm": 1.0, "clip_R1_Nm": 0.999, "sublimit_Nm": 0.2, "sublimit_ratio": 3.0,
    "stall_deg": 0.05, "stall_s": 0.030, "jam_shortfall_deg": 20.0, "jam_penetration_mm": 0.5,
    "censored_R5_Nm": 4.995, "pad_slip_growth_deg": 1.0, "warning_Nm": 0.45, "realism_Nm": 0.2,
    "signature_angle_deg": 45.0, "signature_tol_deg": 10.0,
    "l0_validated_tilt_deg": 5.0, "l0_face_gap_mm": (0.5, 1.5),
    "around_catch_s": 0.05, "sample_every_steps": 20,
}
THRESHOLDS_SHA = hashlib.sha256(json.dumps(THRESHOLDS, sort_keys=True).encode()).hexdigest()


def turn_sign(quarter_turns: int) -> float:
    """Sign of the commanded rotation about the outward face normal (rig.turn: clockwise = negative)."""
    return -1.0 if {1: 1, 2: 2, 3: -1}[quarter_turns] > 0 else 1.0


def commanded_deg(quarter_turns: int) -> float:
    return -90.0 * {1: 1, 2: 2, 3: -1}[quarter_turns]


def wrap180(x):
    return (np.asarray(x, float) + 180.0) % 360.0 - 180.0


def window_mask(turner_adv_deg: np.ndarray) -> np.ndarray:
    lo, hi = THRESHOLDS["window_deg"]
    a = np.asarray(turner_adv_deg, float)
    return (a >= lo) & (a <= hi)


def baseline_Nm(tau: np.ndarray, turner_adv_deg: np.ndarray) -> float | None:
    """Median |tau| over turner angle 20-70 deg from the turn's start (None if no step lies there)."""
    lo, hi = THRESHOLDS["baseline_deg"]
    a = np.asarray(turner_adv_deg, float)
    sel = (a >= lo) & (a <= hi)
    return float(np.median(np.abs(np.asarray(tau, float)[sel]))) if sel.any() else None


def catch_impulse(tau: np.ndarray, win: np.ndarray, baseline: float, dt: float) -> float:
    """Integral of max(0, |tau| - baseline) dt over the window (N m s)."""
    x = np.abs(np.asarray(tau, float)[np.asarray(win, bool)]) - baseline
    return float(np.sum(np.maximum(0.0, x)) * dt)


def stall_intervals(layer_adv_deg: np.ndarray, target_adv_deg: np.ndarray, win: np.ndarray, dt: float) -> list:
    """Section 5 'Stall': inside the window, the layer advances less than 0.05 deg over at least 30 ms while the
    commanded target advances. Every span of L = round(30 ms / dt) steps lying wholly in the window is tested on its
    net advance (end minus start, in the turn direction); qualifying spans are merged. Returns [(i0, i1)] (inclusive
    step indices)."""
    L = max(1, int(round(THRESHOLDS["stall_s"] / dt)))
    la, ta, w = np.asarray(layer_adv_deg, float), np.asarray(target_adv_deg, float), np.asarray(win, bool)
    n = len(la)
    if n <= L:
        return []
    cw = np.concatenate([[0], np.cumsum(~w)])
    i = np.arange(n - L)
    wholly = (cw[i + L + 1] - cw[i]) == 0
    hit = wholly & (la[i + L] - la[i] < THRESHOLDS["stall_deg"]) & (ta[i + L] - ta[i] > 0.0)
    out = []
    for s in np.nonzero(hit)[0]:
        a, b = int(s), int(s + L)
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [tuple(x) for x in out]


def pad_slip_growth(slip_adv_deg: np.ndarray, intervals: list) -> float:
    """Largest growth of pad slip (turner minus layer, in the turn direction) inside any stall interval, measured from
    the interval's start. 0 if there is no stall."""
    s = np.asarray(slip_adv_deg, float)
    g = 0.0
    for a, b in intervals:
        g = max(g, float(np.max(s[a:b + 1]) - s[a]))
    return g


def jam_check(layer_rot_hold_end_deg: float, commanded: float, pen_cc_mm: np.ndarray, t: np.ndarray,
              t_hold_end: float, j3_fired: bool, j3_detail: dict, t_settle_end: float) -> dict:
    """Section 5 J1-J3 (checked first; a jam excludes every other class)."""
    err = float(wrap180(layer_rot_hold_end_deg - commanded))
    j1 = abs(err) > THRESHOLDS["jam_shortfall_deg"]
    pen = np.asarray(pen_cc_mm, float)
    over = np.nonzero(pen > THRESHOLDS["jam_penetration_mm"])[0]
    j2 = bool(len(over))
    return {
        "jam": bool(j1 or j2 or j3_fired),
        "J1": {"fired": bool(j1), "t": float(t_hold_end) if j1 else None, "layer_rotation_deg": layer_rot_hold_end_deg,
               "error_vs_commanded_deg": err, "shortfall_deg": float(abs(err))},
        "J2": {"fired": j2, "t": float(np.asarray(t)[over[0]]) if j2 else None,
               "max_penetration_mm": float(pen.max()) if len(pen) else 0.0},
        "J3": {"fired": bool(j3_fired), "t": float(t_settle_end) if j3_fired else None, **j3_detail},
    }


def catch_class(window_peak: float, baseline: float | None, stalled: bool, rig: str, jam: bool) -> dict:
    """Section 5 catch classes. Under R5 'high' is window peak >= 1.0 N m; under R1 it is the 'clip catch', any window
    step >= 0.999 N m (= window peak >= 0.999). present = high/clip or stall; attenuated = sub-limit only."""
    if jam:
        return {"class": "jam", "high": None, "clip_catch": None, "stall": None, "sub_limit": None,
                "above_warning": None}
    b = 0.0 if baseline is None else baseline
    if rig == "R5":
        high, clip = bool(window_peak >= THRESHOLDS["high_R5_Nm"]), None
    else:
        high, clip = None, bool(window_peak >= THRESHOLDS["clip_R1_Nm"])
    hi = bool(high or clip)
    sub = bool(window_peak >= THRESHOLDS["sublimit_Nm"] and window_peak >= THRESHOLDS["sublimit_ratio"] * b
               and not hi)
    present = hi or bool(stalled)
    cls = "present" if present else ("attenuated" if sub else "absent")
    return {"class": cls, "high": high, "clip_catch": clip, "stall": bool(stalled), "sub_limit": sub,
            "above_warning": bool(window_peak >= THRESHOLDS["warning_Nm"])}


def home_of(name: str) -> tuple[int, int, int] | None:
    if not name.startswith("cubie_") or len(name) != 9:
        return None
    m = {"n": -1, "0": 0, "p": 1}
    return tuple(m[c] for c in name[6:])


def er9_signature(name1: str, name2: str, normal, face_normal) -> bool:
    """Section 9: a corner against a side centre (a centre whose axis is perpendicular to the turn axis), with the
    contact normal within 10 deg of 45 deg to the turn axis."""
    h1, h2 = home_of(name1), home_of(name2)
    if h1 is None or h2 is None:
        return False
    nz = [(int(np.count_nonzero(h)), h) for h in (h1, h2)]
    kinds = sorted(k for k, _ in nz)
    if kinds != [1, 3]:
        return False
    centre = next(h for k, h in nz if k == 1)
    a = np.asarray(face_normal, float)
    if abs(float(np.dot(centre, a))) > 1e-9:
        return False
    n = np.asarray(normal, float)
    ang = float(np.degrees(np.arccos(np.clip(abs(n @ a) / np.linalg.norm(n) / np.linalg.norm(a), 0.0, 1.0))))
    return abs(ang - THRESHOLDS["signature_angle_deg"]) <= THRESHOLDS["signature_tol_deg"]


def validity(layout: str, gap: float, magnet_stats: dict | None) -> dict:
    """Section 8.2. L0: flagged out of regime at near-pair tilt > 5 deg, any perpendicular near pair, or a face gap
    outside 0.5-1.5 mm. W3 (and the S1-only anchored arms): proxy-flagged by construction. none: no question."""
    if layout == "none":
        return {"flagged": False, "kind": "none", "reasons": []}
    if layout == "L0":
        st = magnet_stats or {}
        fg = (gap + 2 * WALL) * 1e3
        lo, hi = THRESHOLDS["l0_face_gap_mm"]
        reasons = []
        tilt = float(st.get("max_near_tilt_deg", 0.0))
        if tilt > THRESHOLDS["l0_validated_tilt_deg"]:
            reasons.append(f"max_near_tilt_deg {tilt:.3f} > 5")
        if int(st.get("near_perpendicular", 0)) > 0:
            reasons.append(f"near_perpendicular {st.get('near_perpendicular')} > 0")
        if not (lo - 1e-12 <= fg <= hi + 1e-12):
            reasons.append(f"face gap {fg:.3f} mm outside 0.5-1.5 mm")
        return {"flagged": bool(reasons), "kind": "out_of_regime" if reasons else "in_regime", "reasons": reasons,
                "face_gap_mm": fg, "disclosed_not_flagged": "corner-edge pairs crossing a turning boundary pass lateral "
                                                            "offsets of 6-8 mm; V3a covers 0-6 mm (review G11)"}
    return {"flagged": True, "kind": "proxy", "reasons": ["off-axis anchor-to-core pairs outside P-60's validated set "
                                                          "(ER9 SUMMARY Limits; review F1)"]}


# ---- section 12: timing and stop rules ------------------------------------------------------------------------------
STOP_PROJECTED_S = 6 * 3600.0
STOP_STAGE4_S = 4 * 3600.0
PER_REPLAY_FACTOR = 3.0
PER_REPLAY_CAP_S = 15 * 60.0
RSS_FACTOR = 2.0


def class_key(layout: str, timestep: float) -> str:
    return f"{layout}@{round(timestep * 1e3, 6):g}ms"


def job_timestep(job: dict) -> float:
    return float(job["overrides"]["m1"].get("timestep", 0.0005))


def job_class(job: dict) -> str:
    return class_key(job["layout"], job_timestep(job))


def class_wall(timing: dict, cls: str) -> tuple[float | None, str]:
    """Wall time (s) of a replay class from the timing test. A class not timed at 0.25 ms is scaled from its 0.5 ms
    value by L0's measured 0.25/0.5 ms ratio (INFERENCE, disclosed in the record)."""
    if cls in timing:
        return float(timing[cls]), "measured"
    layout, ts = cls.split("@")
    base = timing.get(f"{layout}@0.5ms")
    if ts == "0.25ms" and base is not None and "L0@0.25ms" in timing and "L0@0.5ms" in timing:
        return float(base) * float(timing["L0@0.25ms"]) / float(timing["L0@0.5ms"]), "scaled by L0's 0.25/0.5 ms ratio"
    return None, "not timed"


def projected_stage_counts() -> dict:
    """Replays per class: Stage 1 exactly; Stage 2 assuming P-none exists (worst case, 48); Stage 3 at its cap (48),
    charged at the slowest candidate class (none or L0, at 0.5 or 0.25 ms)."""
    s1: dict = {}
    for j in stage1_jobs():
        s1[job_class(j)] = s1.get(job_class(j), 0) + 1
    s2: dict = {}
    for j in stage2_jobs(NOMINAL):
        s2[job_class(j)] = s2.get(job_class(j), 0) + 1
    return {"stage1": s1, "stage2": s2, "stage3_max": 48}


def projection_s(timing_wall: dict) -> dict:
    """Section 12: projected serial wall time of Stages 1-3 from the timing test."""
    counts = projected_stage_counts()
    out, total, missing = {}, 0.0, []
    for stg in ("stage1", "stage2"):
        t = 0.0
        for cls, n in counts[stg].items():
            w, how = class_wall(timing_wall, cls)
            if w is None:
                missing.append(cls)
                continue
            t += n * w
        out[stg] = t
        total += t
    s3cls = [class_key(lay, ts) for lay in CANDIDATE_LAYOUTS for ts in (0.0005, 0.00025)]
    s3w = [class_wall(timing_wall, c)[0] for c in s3cls]
    s3w = [w for w in s3w if w is not None]
    out["stage3_max"] = counts["stage3_max"] * max(s3w) if s3w else None
    if out["stage3_max"] is None:
        missing.append("stage3")
    else:
        total += out["stage3_max"]
    out["total"] = total
    out["missing_classes"] = missing
    out["stop"] = bool(missing) or total > STOP_PROJECTED_S
    out["limit_s"] = STOP_PROJECTED_S
    return out


def per_replay_limit_s(class_wall_s: float | None) -> float:
    """3 x the timing-test wall time of the class, never more than 15 min (no timing value: the 15 min cap)."""
    if class_wall_s is None:
        return PER_REPLAY_CAP_S
    return min(PER_REPLAY_FACTOR * class_wall_s, PER_REPLAY_CAP_S)


def rss_exceeded(rss_mb: float, class_rss_mb: float | None) -> bool:
    return class_rss_mb is not None and rss_mb > RSS_FACTOR * class_rss_mb


def below_floor(free_mb: float | None, floor_mb: float | None) -> bool:
    return floor_mb is not None and free_mb is not None and free_mb < floor_mb


def seq_sim_time_s(n_quarters: list[int], turn_s: float, settle0: float = 0.5,
                   close=0.3, hold=0.3, open_=0.3, settle=0.3) -> float:
    return settle0 + sum(close + turn_s * q + hold + open_ + settle for q in n_quarters)


def stage4_projection_s(first_wall_s: float, first_sim_s: float, all_sim_s: list[float]) -> dict:
    """Section 12: Stage 4 projected from its first sequence trial (wall per simulated second, INFERENCE)."""
    rate = first_wall_s / first_sim_s
    tot = rate * float(sum(all_sim_s))
    return {"wall_per_sim_s": rate, "projected_s": tot, "limit_s": STOP_STAGE4_S, "stop": tot > STOP_STAGE4_S}


# Stage 4 per-trial bound. The protocol's per-replay rule (3 x the class's timing value, at most 15 min) is written for
# single-move replays; a Stage 4 trial is a whole sequence, a 10 s rest or a snap-back, so it has no timing-test class.
# D12 bounds it instead from Stage 4's own first sequence trial: 3 x (that trial's wall per simulated second) x the
# trial's estimated simulated time, at least 5 min (process start and model build dominate short trials) and at most
# 60 min; the first trial itself is bounded at 30 min. A timeout is a stop rule (return to the user).
STAGE4_FIRST_CAP_S = 30 * 60.0
STAGE4_TRIAL_CAP_S = 60 * 60.0
STAGE4_TRIAL_FLOOR_S = 5 * 60.0


def stage4_trial_limit_s(wall_per_sim_s: float | None, est_sim_s: float) -> float:
    if wall_per_sim_s is None:
        return STAGE4_FIRST_CAP_S
    return float(min(STAGE4_TRIAL_CAP_S, max(STAGE4_TRIAL_FLOOR_S, PER_REPLAY_FACTOR * wall_per_sim_s * est_sim_s)))


def stage4_seed_check(job: dict) -> int:
    """The seed the harness uses is job['kw']['seed']: it must equal job['seed'] and pass the guard for the trial."""
    kw_seed = job["kw"]["seed"]
    if kw_seed != job["seed"]:
        raise Refused(f"Stage 4 job {job.get('job_id')}: kw seed {kw_seed!r} != job seed {job['seed']!r}")
    return check_seed(kw_seed, job["trial_kind"])


def seq_guard_rail(drifts: list[float], n_moves: int, aborted: bool) -> dict:
    """Section 7.4 drift guard rail for one sequence trial. A sequence that stopped early (oracle mismatch or abort)
    is 'incomplete': it fails the guard rail but is NOT a drift failure (so it is not read as 'trades the stall for
    drift' and is excluded from Pr7's drift test)."""
    complete = len(drifts) == n_moves and not aborted
    mx = max(drifts) if drifts else None
    fail = bool(complete and mx > 1.0)
    flag = bool(complete and mx >= 0.8)
    return {"max_drift_deg": mx, "n_moves": n_moves, "n_moves_recorded": len(drifts), "complete": complete,
            "incomplete": not complete, "drift_fail": fail, "drift_flag": flag, "pass": bool(complete and not fail)}


def required_table_name(cfg: dict) -> str | None:
    """File name of the derived near-field table er9_probe.table_for would write for an ER9 arm config (None: the
    arm uses M6's N52 table unchanged). Same formula as er9_probe.table_for (diameter 4 mm, length 3 mm)."""
    from rubiknetic.cube_physics.magnets import MagnetParams
    grade, scale = cfg["grade"], cfg.get("scale", 1.0)
    if grade == "N52" and scale == 1.0:
        return None
    mp = MagnetParams(diameter=0.004, length=0.003, grade=grade, scale=scale)
    return f"tilt_{mp.diameter*1e3:g}x{mp.length*1e3:g}_{mp.br:g}T_s{mp.scale:g}_r{mp.r2*1e3:g}_h1.5_q16x48.npz"


def none_replays_clean(records: list[dict]) -> dict:
    """Every no-magnet replay ran with no magnet callback installed and no magnet system (S1b on the actual runs)."""
    bad = [r["job_id"] for r in records if r.get("job", {}).get("kind") == "replay" and r["job"]["layout"] == "none"
           and not r.get("crash") and (r.get("magnet_callback_installed") is not False or r.get("magnets") is not None)]
    n = sum(1 for r in records if r.get("job", {}).get("kind") == "replay" and r["job"]["layout"] == "none"
            and not r.get("crash"))
    return {"n_checked": n, "bad": bad, "pass": bool(n > 0 and not bad)}


# ---- section 8.1 / S7: step counts ---------------------------------------------------------------------------------
def phase_steps(turn_s: float, dt: float, quarters: int = 1, close=0.3, hold=0.3, open_=0.3, settle=0.3) -> dict:
    """Step counts exactly as rig.TurnRig.rotate converts seconds: max(1, round(s / dt)); the ramp is
    round(turn_s * quarters / dt) single steps."""
    f = lambda s: max(1, int(round(s / dt)))  # noqa: E731
    return {"close": f(close), "turn": max(1, int(round(turn_s * quarters / dt))), "hold": f(hold),
            "open": f(open_), "settle": f(settle)}


def s7_check(turn_s: float, dt_a: float = 0.0005, dt_b: float = 0.00025) -> dict:
    """S7: at 0.25 ms the turn, hold, open and settle durations in seconds equal the 0.5 ms values to within one step
    (one step of the coarser timestep), and so does the 0.5 s pre-turn settle of scored.Trial."""
    a, b = phase_steps(turn_s, dt_a), phase_steps(turn_s, dt_b)
    rows = {k: {"s_a": a[k] * dt_a, "s_b": b[k] * dt_b, "diff_s": abs(a[k] * dt_a - b[k] * dt_b)} for k in a}
    pre = {"s_a": int(round(0.5 / dt_a)) * dt_a, "s_b": int(round(0.5 / dt_b)) * dt_b}
    pre["diff_s"] = abs(pre["s_a"] - pre["s_b"])
    rows["trial_settle"] = pre
    ok = all(r["diff_s"] <= max(dt_a, dt_b) + 1e-15 for r in rows.values())
    return {"turn_s_per_quarter": turn_s, "rows": rows, "pass": bool(ok)}


# ---- storage selection (section 9) ----------------------------------------------------------------------------------
def stored_steps(n: int, abs_step0: int, win: np.ndarray, events: list[int], intervals: list, dt: float) -> np.ndarray:
    """Indices of the per-step series kept in the record: every step in the window, every step within 0.05 s of a
    catch event (snapshot steps) or of a stall interval, and every 20th step (absolute step count, as ER9) elsewhere."""
    keep = np.zeros(n, bool)
    keep[np.asarray(win, bool)] = True
    absn = abs_step0 + 1 + np.arange(n)
    keep[absn % THRESHOLDS["sample_every_steps"] == 0] = True
    D = int(round(THRESHOLDS["around_catch_s"] / dt))
    for e in events:
        if e is not None and 0 <= e < n:
            keep[max(0, e - D):min(n, e + D + 1)] = True
    for a, b in intervals:
        keep[max(0, a - D):min(n, b + D + 1)] = True
    return np.nonzero(keep)[0]


def jsonable(x):
    if hasattr(x, "tolist"):
        return x.tolist()
    if isinstance(x, (set, frozenset)):
        return sorted(x)
    return str(x)
