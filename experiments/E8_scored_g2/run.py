"""Scored G2 runner (experiments/PHASE_2_G2_PREREGISTRATION.md; DRAFT, not in force: scored starts are refused until
the pre-registration is frozen, see FROZEN below).

Run procedure (as the G1 runners, M5 §2, simplified to one results folder):
  * record key (exp, trial ID); one first start with an empty folder writes MANIFEST.json (trial list, environment,
    frozen paths, commit, artifact SHA-256s), linked atomically; a manifest that exists means every later start is a
    resume;
  * STARTS.txt (append-only start log, the resume plan logged before it is applied), LEDGER.txt (one line per record
    with its SHA-256);
  * records are written by the parent only: temporary file, fsync, os.link to the final name (never overwritten),
    unlink, ledger line;
  * resume: the trial list, environment, artifact SHA-256s and frozen paths must equal the manifest's; orphan in-flight
    temporary files (<exp>/.<tid>.json.tmp of a manifest trial) are moved to _interrupted/ (logged); records without
    a ledger line are reconciled; any other temporary file, a duplicate or record-less ledger key, or a file a
    verdict would count as INVALID stops the resume; each start logs the records present at it;
  * harness exceptions become failing records; MemoryError, OSError, a magnet-availability refusal or a broken worker
    pool are interruptions (exit 3, resume with the same command);
  * one trial per worker process (spawn, max_tasks_per_child=1), so module settings never leak between trials;
  * location check: no path in a OneDrive folder; the rubiknetic package from this repository.
Usage (WSL, repo root):
  python experiments/E8_scored_g2/run.py all [--jobs N] [--dry-run]
  python experiments/E8_scored_g2/run.py smoke --smoke-dir DIR [--jobs N] [--stop-after N --stop-point P]
Exit codes: 0 complete, 2 refused, 3 interrupted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import re
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

OUT = HERE / "results"
MANIFEST, STARTS, LEDGER, INTERRUPTED = "MANIFEST.json", "STARTS.txt", "LEDGER.txt", "_interrupted"
ENV_COMPARED = ("mujoco", "numpy", "scipy", "python", "cpu")
SCORED_SEEDS = (30000, 30999)
SMOKE_SEED_BASE = 29100                  # pilot range 29000-29999 (never scored)
FROZEN = False                           # set True only when the pre-registration is frozen (with its review record)
FROZEN_PATHS = [                         # review 1 item 5: every repository module a trial loads (tested), and data
    "experiments/PHASE_2_G2_PREREGISTRATION.md",
    "experiments/E8_scored_g2/run.py", "experiments/E8_scored_g2/trials.py", "experiments/E8_scored_g2/analyze.py",
    "experiments/E8_scored_g2/selfcheck.py", "tests/test_scored_g2.py",
    "experiments/D18_two_arm_m7/two_arm.py", "experiments/D18_two_arm_m7/layout.py",
    "experiments/D17_real_holder_m7/hold.py", "experiments/D17_real_holder_m7/turn.py",
    "experiments/D16_free_core_m7/grip_probe.py",
    "experiments/P2_robot_model/build_model.py",
    "experiments/E7_scored_m7/run.py", "experiments/E5_scored_m5/run.py", "experiments/E4_scored_m4/run.py",
    "experiments/E1_scored/run.py",      # review 3 item 2: executed by E4's runner via spec_from_file_location
    "experiments/D8_alignment/magnets.py", "experiments/D8_alignment/d8_1b_stage1.py",
    "experiments/D8_alignment/results/d8_1b_checks*.json",
    "experiments/D10_m5_rest_diagnostic/d10_rest.py", "experiments/D11_rest_slip_count/d11_analyze.py",
    "experiments/D13_rest_slip_mechanism/d13_run.py", "experiments/D13_rest_slip_mechanism/d13_analyze.py",
    "src/rubiknetic/__init__.py", "src/rubiknetic/cube_physics", "src/rubiknetic/cube_logic",
]
MIN_FREE_GB = 2.0
MAX_STARTS = 6                           # review 3 S5: the first start and at most 5 resumes; then G2 is not passed


class Interrupted(Exception):
    """The run stopped before completing; resume with the same command."""


# ---- the job list (pre-registration §3; counts P-109 (4)) ------------------------------------------------------------
def job(exp: str, tid: str, kind: str, kw: dict, reported_only: bool = False) -> dict:
    return {"exp": exp, "tid": tid, "kind": kind, "kw": kw, "reported_only": reported_only}


SENS = [("kp_x0.5", {"kp": 2000.0}), ("kp_x1.5", {"kp": 6000.0}), ("mu0.5", {"pad_mu": 0.5}),
        ("grip10", {"grip": 10.0}), ("grip30", {"grip": 30.0}), ("grip50_stress", {"grip": 50.0}),
        ("rigid_pads", {"tip_solref": 0.001}), ("offset2mm", {"extra_offset_m": [0.0, 0.002, 0.002]})]


def build_jobs(base: int = 30000) -> list[dict]:
    from trials import NEG_CASES, random_u_sequence
    J = []
    J += [job("G2-1", f"hold60_s{base + i}", "hold", {"seed": base + i, "hold_s": 60.0}) for i in range(20)]
    J += [job("G2-2", f"U_s{base + 100 + i}", "seq", {"seed": base + 100 + i, "moves": "U"}) for i in range(20)]
    J += [job("G2-2", f"Up_s{base + 120 + i}", "seq", {"seed": base + 120 + i, "moves": "U'"}) for i in range(20)]
    J += [job("G2-3", f"U2_s{base + 200 + i}", "seq", {"seed": base + 200 + i, "moves": "U2"}) for i in range(20)]
    J += [job("G2-4", f"seq5_s{base + 300 + i}", "seq", {"seed": base + 300 + i, "moves": "U U' U2 U' U"})
          for i in range(20)]
    J += [job("G2-4", f"rand10_s{base + 320 + i}", "seq",
              {"seed": base + 320 + i, "moves": random_u_sequence(base + 320 + i)}) for i in range(20)]
    J += [job("G2-6", f"{name}_s{base + 600 + i}", "sens",
              {"seed": base + 600 + i, "moves": "U U' U2 U' U", "overrides": ov}, reported_only=True)
          for i, (name, ov) in enumerate(SENS)]
    from trials import NEG_REPORTED_ONLY
    J += [job("G2-7", f"{c}_s{base + 700 + 2 * i + k}", "neg", {"seed": base + 700 + 2 * i + k, "case": c},
              reported_only=c in NEG_REPORTED_ONLY)
          for i, c in enumerate(NEG_CASES) for k in range(2)]
    return J


def smoke_jobs() -> list[dict]:
    b = SMOKE_SEED_BASE
    return [job("G2-1", f"hold5_s{b}", "hold", {"seed": b, "hold_s": 5.0}),
            job("G2-2", f"U_s{b + 1}", "seq", {"seed": b + 1, "moves": "U"}),
            job("G2-3", f"U2_s{b + 2}", "seq", {"seed": b + 2, "moves": "U2"}),
            job("G2-4", f"seq3_s{b + 3}", "seq", {"seed": b + 3, "moves": "U U' U2"}),
            job("G2-7", f"jam_s{b + 4}", "neg", {"seed": b + 4, "case": "jam"})]


def pilot_jobs() -> list[dict]:
    """P-5 pilots (UNSCORED; user 2026-11-26: "Full pilot set"), pilot seeds 29200-29299."""
    from trials import random_u_sequence
    off = {"ft_stop": 5.0}                     # measurement runs: the F/T stop effectively disabled
    J = [job("P-U", f"U_s{29200 + i}", "seq", {"seed": 29200 + i, "moves": "U", "overrides": off}) for i in range(30)]
    for i, stop in enumerate([0.6] * 3 + [0.8] * 4 + [1.0] * 3):
        J.append(job("P-jam", f"jam{stop:g}_s{29230 + i}", "neg",
                     {"seed": 29230 + i, "case": "jam", "overrides": {"ft_stop": stop}}))
    for i, c in enumerate(("two_layer", "offcentre", "collision", "open_midturn")):
        J += [job("P-neg", f"{c}_s{29240 + 2 * i + k}", "neg", {"seed": 29240 + 2 * i + k, "case": c})
              for k in range(2)]
    J += [job("P-hold", f"hold60_s{29250 + i}", "hold", {"seed": 29250 + i, "hold_s": 60.0}) for i in range(4)]
    J += [job("P-rand", f"rand10_s{29260 + i}", "seq",
              {"seed": 29260 + i, "moves": random_u_sequence(29260 + i), "overrides": off}) for i in range(4)]
    return J


def pilot2_jobs() -> list[dict]:
    """Revision-2 pilot (UNSCORED; review 1 suggestion 9 and a check of the revision-2 criteria), seeds 29300-29399:
    20 U' and 20 U2 single turns with the F/T stop disabled (first-turn torque tail), 4 x U U' U2 U' U and 2 x 60 s
    holds at the fixed settings, and 2 each of the jam, two_layer, collision and open_midturn cases."""
    off = {"ft_stop": 5.0}
    J = [job("P2-Up", f"Up_s{29300 + i}", "seq", {"seed": 29300 + i, "moves": "U'", "overrides": off}) for i in range(20)]
    J += [job("P2-U2", f"U2_s{29320 + i}", "seq", {"seed": 29320 + i, "moves": "U2", "overrides": off})
          for i in range(20)]
    J += [job("P2-seq", f"seq5_s{29340 + i}", "seq", {"seed": 29340 + i, "moves": "U U' U2 U' U"}) for i in range(4)]
    J += [job("P2-hold", f"hold60_s{29344 + i}", "hold", {"seed": 29344 + i, "hold_s": 60.0}) for i in range(2)]
    for i, c in enumerate(("jam", "two_layer", "collision", "open_midturn")):
        J += [job("P2-neg", f"{c}_s{29346 + 2 * i + k}", "neg", {"seed": 29346 + 2 * i + k, "case": c}) for k in range(2)]
    return J


def pilot3_jobs() -> list[dict]:
    """Review 2 items 1-2 pilot (UNSCORED; seeds 29400-29499), at the configuration to be frozen:
    first turns with the U face forced to an extreme start misalignment, F/T stop disabled (U' and U2 at -0.80 ...
    -1.00 deg, 10 each; U' and U2 at +0.80 ... +1.00 deg, 5 each; U at -1.0 and +1.0 deg, 2 each), and a confirmation
    set: 4 x two_layer, 2 x jam, 8 x 10-move random sequences."""
    from trials import random_u_sequence
    J, s = [], 29400
    for mv, name in (("U'", "Up"), ("U2", "U2")):
        for i, deg in enumerate([-0.80, -0.85, -0.90, -0.95, -1.00] * 2):
            J.append(job("P3-ext", f"{name}_m{abs(deg):.2f}_{i}_s{s}", "seq",
                         {"seed": s, "moves": mv, "overrides": {"ft_stop": 5.0, "misalign_override": {"U": deg}}}))
            s += 1
        for i, deg in enumerate([0.80, 0.85, 0.90, 0.95, 1.00]):
            J.append(job("P3-ext", f"{name}_p{deg:.2f}_s{s}", "seq",
                         {"seed": s, "moves": mv, "overrides": {"ft_stop": 5.0, "misalign_override": {"U": deg}}}))
            s += 1
    for deg in (-1.0, -1.0, 1.0, 1.0):
        J.append(job("P3-ext", f"U_{'m' if deg < 0 else 'p'}1.00_s{s}", "seq",
                     {"seed": s, "moves": "U", "overrides": {"ft_stop": 5.0, "misalign_override": {"U": deg}}}))
        s += 1
    s = 29440
    J += [job("P3-conf", f"two_layer_s{s + i}", "neg", {"seed": s + i, "case": "two_layer"}) for i in range(4)]
    J += [job("P3-conf", f"jam_s{s + 4 + i}", "neg", {"seed": s + 4 + i, "case": "jam"}) for i in range(2)]
    J += [job("P3-conf", f"rand10_s{s + 6 + i}", "seq", {"seed": s + 6 + i, "moves": random_u_sequence(s + 6 + i)})
          for i in range(8)]
    return J


def pilot4_jobs() -> list[dict]:
    """Magnets-on re-pilot (UNSCORED; P-130/P-131, user: "Full re-pilot"), new seeds 29500-29699. Every earlier D18/G2
    pilot ran without the L0 magnets (review 4 N1). This set repeats all of them with the magnets active:
    - first turns with the F/T stop disabled: 30 U, 20 U', 20 U2 (torque tail, turn error, t0 offset);
    - the pilot-3 forced-extreme first turns (U face at +-0.80 ... +-1.00 deg), 34;
    - at the configuration to be frozen (F/T stop 1.0 N.m): 6 jam, 6 two_layer, 2 each of collision, open_midturn and
      offcentre, 6 x 60 s holds, 4 x U U' U2 U' U, and 12 x 10-move random sequences."""
    from trials import random_u_sequence
    off = {"ft_stop": 5.0}
    J = [job("P4-U", f"U_s{29500 + i}", "seq", {"seed": 29500 + i, "moves": "U", "overrides": off}) for i in range(30)]
    J += [job("P4-Up", f"Up_s{29530 + i}", "seq", {"seed": 29530 + i, "moves": "U'", "overrides": off})
          for i in range(20)]
    J += [job("P4-U2", f"U2_s{29550 + i}", "seq", {"seed": 29550 + i, "moves": "U2", "overrides": off})
          for i in range(20)]
    s = 29570
    for mv, name in (("U'", "Up"), ("U2", "U2")):
        for i, deg in enumerate([-0.80, -0.85, -0.90, -0.95, -1.00] * 2):
            J.append(job("P4-ext", f"{name}_m{abs(deg):.2f}_{i}_s{s}", "seq",
                         {"seed": s, "moves": mv, "overrides": {**off, "misalign_override": {"U": deg}}}))
            s += 1
        for deg in (0.80, 0.85, 0.90, 0.95, 1.00):
            J.append(job("P4-ext", f"{name}_p{deg:.2f}_s{s}", "seq",
                         {"seed": s, "moves": mv, "overrides": {**off, "misalign_override": {"U": deg}}}))
            s += 1
    for deg in (-1.0, -1.0, 1.0, 1.0):
        J.append(job("P4-ext", f"U_{'m' if deg < 0 else 'p'}1.00_s{s}", "seq",
                     {"seed": s, "moves": "U", "overrides": {**off, "misalign_override": {"U": deg}}}))
        s += 1
    J += [job("P4-neg", f"jam_s{29610 + i}", "neg", {"seed": 29610 + i, "case": "jam"}) for i in range(6)]
    J += [job("P4-neg", f"two_layer_s{29620 + i}", "neg", {"seed": 29620 + i, "case": "two_layer"}) for i in range(6)]
    for i, c in enumerate(("collision", "open_midturn", "offcentre")):
        J += [job("P4-neg", f"{c}_s{29630 + 2 * i + k}", "neg", {"seed": 29630 + 2 * i + k, "case": c})
              for k in range(2)]
    J += [job("P4-hold", f"hold60_s{29640 + i}", "hold", {"seed": 29640 + i, "hold_s": 60.0}) for i in range(6)]
    J += [job("P4-seq", f"seq5_s{29650 + i}", "seq", {"seed": 29650 + i, "moves": "U U' U2 U' U"}) for i in range(4)]
    J += [job("P4-rand", f"rand10_s{29660 + i}", "seq",
              {"seed": 29660 + i, "moves": random_u_sequence(29660 + i)}) for i in range(12)]
    return J


def key_of(j: dict) -> tuple[str, str]:
    return j["exp"], j["tid"]


# ---- one trial (worker side) ------------------------------------------------------------------------------------------
def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def metadata(j: dict) -> dict:
    return {"experiment": j["exp"], "trial_id": j["tid"], "kind": j["kind"], "spec": j["kw"],
            "reported_only": j["reported_only"], "source_commit": j.get("commit"), "environment": j.get("env"),
            "smoke": j.get("smoke", False), "scored": j.get("scored", False), "head": j.get("head"),
            "mechanism": "M7 free core, two xArm7"}


def exception_record(j: dict, exc: BaseException) -> dict:
    rec = {"harness_exception": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
           "pass": False, "fail_reasons": [f"harness exception: {type(exc).__name__}: {exc}"]}
    rec.update(metadata(j))
    return rec


# Model-load failures (pilot 3, P-127; the P-115 refusal): reading the robot meshes, calibration or magnet records from
# /mnt/c under parallel load occasionally returns an empty file. Review 3 item 1: classified by PHASE, not by message.
# Any exception (OSError included) raised before the trial's first control step is a load error: the trial is retried in
# the same worker (at most LOAD_ATTEMPTS times) and, if it persists, the run is interrupted (resume), never recorded as
# a failed trial. A magnet-availability refusal is always an interruption. After the first step, MemoryError and
# OSError interrupt the run and any other exception is a failing record.
LOAD_ATTEMPTS = 3


def run_job(j: dict) -> tuple[tuple, dict]:
    """Runs one trial in this (fresh) worker: see the load-error rule above."""
    import trials as T
    load0 = os.getloadavg()[0] if hasattr(os, "getloadavg") else None
    retries = []
    for attempt in range(1, LOAD_ATTEMPTS + 1):
        T.reset_phase()
        try:
            t0 = time.perf_counter()
            rec = T.run_trial(j["kind"], j["kw"])
            rec.update(metadata(j))
            rec["loadavg_start"], rec["wall_s"], rec["load_retries"] = load0, time.perf_counter() - t0, retries
            json.dumps(rec, default=list)        # a record that cannot be saved is a failed trial, not a crash
            break
        except MemoryError:
            raise
        except Exception as e:  # noqa: BLE001
            if isinstance(e, T.Refused) or not T.simulation_started():
                retries.append(f"{type(e).__name__}: {e}")
                if attempt < LOAD_ATTEMPTS:
                    time.sleep(2.0)
                    continue
                raise OSError(f"model load failed {LOAD_ATTEMPTS} times: {retries}") from e
            if isinstance(e, OSError):
                raise
            rec = exception_record(j, e)
            rec["load_retries"] = retries
            break
    return key_of(j), rec


# ---- files (parent only) ------------------------------------------------------------------------------------------------
def _append_line(path: Path, obj: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record_path(out: Path, key: tuple) -> Path:
    return out / key[0] / f"{key[1]}.json"


def write_record(out: Path, key: tuple, rec: dict, start_k: int, stop_point: str | None = None) -> str:
    final = record_path(out, key)
    final.parent.mkdir(parents=True, exist_ok=True)
    tmp = final.parent / f".{final.stem}.json.tmp"
    data = json.dumps(rec, indent=1, default=list).encode()
    with open(tmp, "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    if stop_point == "after_tmp":
        os._exit(3)
    os.link(tmp, final)
    if stop_point == "after_link":
        os._exit(3)
    os.unlink(tmp)
    sha = _sha(data)
    _append_line(out / LEDGER, {"start": start_k, "exp": key[0], "tid": key[1], "sha256": sha, "reconciled": False})
    if stop_point == "after_ledger":
        os._exit(3)
    return sha


def read_lines(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def _norm(x):
    return json.loads(json.dumps(x, sort_keys=True, default=list))


def artifacts() -> dict:
    """SHA-256 of the physics-defining files git cannot see or that live outside the frozen code (review 1 item 5):
    the generated robot model, its gripper calibration, every mesh it references, the magnet near-field table in use,
    and the V3 check records."""
    import glob
    gen = REPO / "third_party_cad" / "robot" / "generated"
    xml_p = gen / "xarm7_g2_1305+.xml"
    files = [xml_p, gen / "xarm7_g2_1305+_gripper_calibration.json"]
    txt = xml_p.read_text()
    m = re.search(r'meshdir="([^"]+)"', txt)
    meshdir = (xml_p.parent / m.group(1)).resolve() if m else xml_p.parent
    for f in sorted(set(re.findall(r'<mesh[^>]*file="([^"]+)"', txt))):
        files.append((meshdir / f).resolve())
    import trials as T
    mp = T.TA.H.R.magnet_params_for({})
    files.append(Path(T.TA.H.M4.table_path(mp)))
    files += [Path(x) for x in sorted(glob.glob(str(REPO / "experiments/D8_alignment/results/d8_1b_checks*.json")))]
    out = {}
    for f in files:
        f = Path(f).resolve()
        out[str(f.relative_to(REPO)) if f.is_relative_to(REPO) else str(f)] = _sha(f.read_bytes())
    return out


def manifest_body(jobs: list[dict], commit: str, env: dict, arts: dict | None = None) -> dict:
    return {"gate": "G2", "commit": commit, "environment": env, "environment_compared": list(ENV_COMPARED),
            "frozen_paths": FROZEN_PATHS, "artifacts": arts or {},
            "trials": [{"exp": j["exp"], "tid": j["tid"], "kind": j["kind"], "kw": j["kw"],
                        "reported_only": j["reported_only"]} for j in jobs]}


def write_manifest(out: Path, body: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    data = json.dumps({**body, "created": _now()}, indent=1, sort_keys=True, default=list).encode()
    tmp = out.parent / f".{out.name}.{MANIFEST}.tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.link(tmp, out / MANIFEST)                  # fails if a manifest exists: one first start only
    os.unlink(tmp)


def _git(*args: str) -> str:
    import subprocess
    cmd = ["git", "-c", "core.filemode=false", "-c", "safe.directory=*", "-C", str(REPO), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()


def ledger_problems(out: Path, manifest: dict) -> list[str]:
    """Review 1 item 4 (b): a ledger key with more than one line, or whose record is missing, means a record was
    deleted or rewritten; the run is then INVALID and may not be resumed."""
    seen: dict = {}
    for x in read_lines(out / LEDGER):
        k = (x["exp"], x["tid"])
        seen[k] = seen.get(k, 0) + 1
    keys = {(t["exp"], t["tid"]) for t in manifest["trials"]}
    probs = [f"ledger key {k} has {n} lines" for k, n in seen.items() if n > 1]
    probs += [f"ledger key {k} has no record" for k in seen if not record_path(out, k).exists()]
    probs += [f"ledger key {k} is not a manifest trial" for k in seen if k not in keys]
    return probs


def resume_problems(manifest: dict, body: dict, head: str, check_git: bool = True) -> list[str]:
    probs = []
    if _norm(manifest.get("trials")) != _norm(body["trials"]):
        probs.append("trials differ from the manifest")
    if _norm(manifest.get("artifacts", {})) != _norm(body.get("artifacts", {})):
        changed = sorted(k for k in set(manifest.get("artifacts", {})) | set(body.get("artifacts", {}))
                         if manifest.get("artifacts", {}).get(k) != body.get("artifacts", {}).get(k))
        probs.append(f"artifact SHA-256s differ from the manifest: {changed}")
    for k in ENV_COMPARED:
        if manifest.get("environment", {}).get(k) != body["environment"].get(k):
            probs.append(f"environment field {k} differs from the manifest")
    base = manifest["commit"].split("+")[0]
    if check_git and base != head:
        diff = _git("diff", "--name-only", base, head, "--", *manifest["frozen_paths"])
        if diff:
            probs.append(f"frozen paths differ between the manifest commit and HEAD: {diff}")
    return probs


def foreign_files(out: Path, starts: list[dict], manifest: dict) -> list[str]:
    logged = {o["moved_to"] for s in starts for o in s.get("orphans", [])}
    records = {record_path(out, (t["exp"], t["tid"])) for t in manifest["trials"]}
    exps = {t["exp"] for t in manifest["trials"]}
    bad = []
    for p in out.iterdir():
        if p.is_file():
            if p.name not in (MANIFEST, STARTS, LEDGER):
                bad.append(p.name)
        elif p.name not in exps and p.name != INTERRUPTED:
            bad.append(f"{p.name}/ (directory not in the manifest)")
        elif p.name == INTERRUPTED:
            bad += [str(f.relative_to(out)) for f in p.iterdir() if str(f.relative_to(out)) not in logged]
        else:
            for f in p.iterdir():
                if not (f in records or is_inflight_tmp(out, str(f.relative_to(out)), manifest)):
                    bad.append(str(f.relative_to(out)))
    return bad


def is_inflight_tmp(out: Path, rel: str, manifest: dict) -> bool:
    """Review 2 item 4: the only temporary file the procedure leaves is <exp>/.<tid>.json.tmp of a manifest trial."""
    keys = {(t["exp"], t["tid"]) for t in manifest["trials"]}
    parts = Path(rel).parts
    return (len(parts) == 2 and parts[1].startswith(".") and parts[1].endswith(".json.tmp")
            and (parts[0], parts[1][1:-len(".json.tmp")]) in keys)


def plan_resume(out: Path, manifest: dict, start_k: int) -> dict:
    orphans, reconciled = [], []
    for tmp in sorted(p for p in out.glob("*/.*.json.tmp") if is_inflight_tmp(out, str(p.relative_to(out)), manifest)):
        dest = out / INTERRUPTED / f"k{start_k}__{tmp.parent.name}__{tmp.name}"
        orphans.append({"path": str(tmp.relative_to(out)), "moved_to": str(dest.relative_to(out)),
                        "sha256": _sha(tmp.read_bytes())})
    ledger = {(x["exp"], x["tid"]) for x in read_lines(out / LEDGER)}
    for t in manifest["trials"]:
        key = (t["exp"], t["tid"])
        p = record_path(out, key)
        if p.exists() and key not in ledger:
            data = p.read_bytes()
            json.loads(data)                       # an unreadable record stops the resume (INVALID)
            reconciled.append({"key": list(key), "sha256": _sha(data)})
    return {"orphans": orphans, "reconciled": reconciled}


def apply_resume(out: Path, plan: dict, start_k: int) -> None:
    for o in plan["orphans"]:
        src, dest = out / o["path"], out / o["moved_to"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.link(src, dest)
        os.unlink(src)
    for r in plan["reconciled"]:
        _append_line(out / LEDGER, {"start": start_k, "exp": r["key"][0], "tid": r["key"][1],
                                    "sha256": r["sha256"], "reconciled": True})


def execute(out: Path, jobs: list[dict], commit: str, env: dict, head: str, n_workers: int, runner=run_job,
            stop_after: int | None = None, stop_point: str | None = None, check_git: bool = True, log=print,
            arts: dict | None = None) -> int:
    body = manifest_body(jobs, commit, env, arts)
    man = out / MANIFEST
    if not man.exists():
        if out.exists() and any(out.iterdir()):
            raise SystemExit(f"refusing first start: {out} is not empty and has no manifest")
        write_manifest(out, body)
        start_k, plan = 1, {"orphans": [], "reconciled": []}
    else:
        manifest = json.loads(man.read_text())
        starts = read_lines(out / STARTS)
        if len(starts) >= MAX_STARTS:
            raise SystemExit(f"refusing resume: {len(starts)} starts used (the first and {MAX_STARTS - 1} resumes); "
                             "G2 is not passed by this pre-registration (§6)")
        probs = resume_problems(manifest, body, head, check_git)
        probs += [f"file that would make the run INVALID: {f}" for f in foreign_files(out, starts, manifest)
                  if not is_inflight_tmp(out, f, manifest)]
        probs += ledger_problems(out, manifest)
        if probs:
            raise SystemExit("refusing resume:\n  " + "\n  ".join(probs))
        commit = manifest["commit"]
        start_k = len(starts) + 1
        plan = plan_resume(out, manifest, start_k)
    present = sorted([t["exp"], t["tid"]] for t in body["trials"] if record_path(out, (t["exp"], t["tid"])).exists())
    _append_line(out / STARTS, {"k": start_k, "time": _now(), "head": head, "present": present, **plan})
    if start_k > 1:
        apply_resume(out, plan, start_k)
    for j in jobs:
        j["commit"], j["env"], j["head"] = commit, env, head
    todo = [j for j in jobs if not record_path(out, key_of(j)).exists()]
    todo.sort(key=lambda j: -(len(j["kw"].get("moves", "").split()) + j["kw"].get("hold_s", 0) / 10))
    log(f"start {start_k}: commit {commit}; {len(todo)} of {len(jobs)} trials to run; orphans moved "
        f"{len(plan['orphans'])}; ledger lines reconciled {len(plan['reconciled'])}")
    written = 0

    def _write(key, rec):
        nonlocal written
        sp = stop_point if (stop_after is not None and written + 1 == stop_after) else None
        write_record(out, key, rec, start_k, sp)
        written += 1
        log(f"{'PASS' if rec['pass'] else 'FAIL'} {key[0]}/{key[1]} {'; '.join(rec['fail_reasons'])}")
        if stop_after is not None and written >= stop_after:
            raise Interrupted(f"stopped after {written} records (--stop-after)")

    if runner is not run_job:              # injected runners (unit tests) run in-process; real trials never do
        for j in todo:
            try:
                key, rec = runner(j)
            except Exception as e:  # noqa: BLE001  (MemoryError, OSError, Refused)
                raise Interrupted(f"{type(e).__name__}: {e}") from e
            _write(key, rec)
        return written
    ex = ProcessPoolExecutor(max_workers=max(1, n_workers), mp_context=multiprocessing.get_context("spawn"),
                             max_tasks_per_child=1)   # review 1 item 6: one trial per spawned process, always
    try:
        futs = [ex.submit(runner, j) for j in todo]
        for fut in as_completed(futs):
            try:
                key, rec = fut.result()
            except Exception as e:  # noqa: BLE001  (BrokenProcessPool, MemoryError, OSError, Refused)
                raise Interrupted(f"{type(e).__name__}: {e}") from e
            _write(key, rec)
    finally:
        ex.shutdown(wait=True, cancel_futures=True)
    return written


# ---- environment and location -------------------------------------------------------------------------------------------
ONEDRIVE_DIR = re.compile(r"(?i)^onedrive\b")


def location_problems(paths: dict) -> list[str]:
    probs = []
    for label, path in paths.items():
        real = Path(path).resolve()
        hits = [c for c in real.parts if ONEDRIVE_DIR.match(c)]
        if hits:
            probs.append(f"{label} {real} is inside a OneDrive folder ({hits[0]!r})")
    import rubiknetic
    if not Path(rubiknetic.__file__).resolve().is_relative_to((REPO / "src").resolve()):
        probs.append(f"the rubiknetic package is imported from {rubiknetic.__file__}, not from {REPO / 'src'}")
    return probs


def environment() -> dict:
    import platform

    import mujoco
    import numpy
    import scipy
    cpu = platform.processor() or platform.machine()
    try:
        cpu = next(x.split(":", 1)[1].strip() for x in Path("/proc/cpuinfo").read_text().splitlines()
                   if x.startswith("model name"))
    except (OSError, StopIteration):
        pass
    return {"mujoco": mujoco.__version__, "numpy": numpy.__version__, "scipy": scipy.__version__,
            "python": platform.python_version(), "cpu": cpu, "os": platform.platform(), "n_cpu": os.cpu_count()}


def require_clean_commit() -> str:
    dirty = _git("status", "--porcelain", "--", *FROZEN_PATHS)
    if dirty:
        raise SystemExit("refusing to run scored trials: uncommitted changes in frozen paths:\n" + dirty)
    return _git("rev-parse", "HEAD")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment", choices=["all", "smoke", "pilot", "pilot2", "pilot3", "pilot4"])
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke-dir", type=Path)
    ap.add_argument("--stop-after", type=int)
    ap.add_argument("--stop-point", choices=["after_tmp", "after_link", "after_ledger"], default="after_ledger")
    a = ap.parse_args(argv)
    smoke = a.experiment in ("smoke", "pilot", "pilot2", "pilot3", "pilot4")      # unscored, into --smoke-dir
    if smoke != (a.smoke_dir is not None):
        raise SystemExit("'smoke'/'pilot' require --smoke-dir, and --smoke-dir is only for them")
    if a.stop_after is not None and not smoke:
        raise SystemExit("--stop-after is for the smoke test only")
    if smoke:
        sd = a.smoke_dir.resolve()
        if sd == OUT.resolve() or sd.is_relative_to(OUT.resolve()):
            raise SystemExit(f"refusing: --smoke-dir {a.smoke_dir} would write into the scored folder")
    jobs = {"pilot": pilot_jobs, "pilot2": pilot2_jobs, "pilot3": pilot3_jobs, "pilot4": pilot4_jobs,
            "smoke": smoke_jobs, "all": build_jobs}[a.experiment]()
    if not smoke:
        seeds = [j["kw"]["seed"] for j in jobs]
        assert all(SCORED_SEEDS[0] <= s <= SCORED_SEEDS[1] for s in seeds) and len(set(seeds)) == len(seeds)
    if a.dry_run:
        by = {}
        for j in jobs:
            by.setdefault(j["exp"], []).append(j)
        for e, js in sorted(by.items()):
            print(f"{e}: {len(js)} trials ({sum(x['reported_only'] for x in js)} reported only)")
        print(f"{len(jobs)} trials")
        return
    if not smoke and not FROZEN:
        raise SystemExit("refusing scored start: the G2 pre-registration is not frozen (FROZEN = False)")
    probs = location_problems({"repository": REPO, "results folder": a.smoke_dir if smoke else OUT})
    if probs:
        raise SystemExit("refusing: " + "; ".join(probs))
    head = _git("rev-parse", "HEAD")
    commit = head + "+smoke" if smoke else require_clean_commit()
    env = environment()
    for j in jobs:
        j["smoke"], j["scored"] = smoke, not smoke
    out = a.smoke_dir / "results" if smoke else OUT
    import shutil
    free_gb = shutil.disk_usage(out.parent if out.parent.exists() else REPO).free / 1e9
    if free_gb < MIN_FREE_GB:
        raise SystemExit(f"refusing: {free_gb:.1f} GB free < {MIN_FREE_GB} GB")
    arts = artifacts()
    t0 = time.perf_counter()
    try:
        n = execute(out, jobs, commit, env, head, a.jobs, stop_after=a.stop_after,
                    stop_point=a.stop_point if a.stop_after else None, log=lambda s: print(s, flush=True), arts=arts)
    except Interrupted as e:
        print(f"INTERRUPTED after {time.perf_counter() - t0:.0f} s: {e}. Resume with the same command.", flush=True)
        sys.exit(3)
    print(f"complete: {n} records written this start in {time.perf_counter() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
