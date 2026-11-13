"""E1-0 calibration pilot (UNSCORED). Every configuration tried is recorded,
including failures, in results/<tag>.json.

Usage (WSL2):  uv run python experiments/E1-0_calibration/run.py <tag> key=value ...
Each key=value overrides one M1Params field (tuples as comma lists).
Special keys: seq=R_U_R'_U' (underscores = spaces); scramble=N:SEED runs an
N-move seeded scramble followed by its inverse.
"""

from __future__ import annotations

import json
import sys
from dataclasses import fields
from pathlib import Path

from rubiknetic.cube_logic import invert, parse, random_scramble, to_string
from rubiknetic.cube_physics.m1_model import M1Params
from rubiknetic.cube_physics.trials import environment, run_sequence

SEQUENCE = "U U' R R' F F'"


def _coerce(name: str, raw: str):
    default = {f.name: f.default for f in fields(M1Params)}.get(name)
    if default is None and name not in {f.name for f in fields(M1Params)}:
        raise SystemExit(f"unknown parameter {name}")
    if isinstance(getattr(M1Params(), name), tuple):
        return tuple(float(x) for x in raw.split(","))
    if isinstance(getattr(M1Params(), name), bool):
        return raw.lower() in ("1", "true", "yes")
    if isinstance(getattr(M1Params(), name), int):
        return int(raw)
    if isinstance(getattr(M1Params(), name), float):
        return float(raw)
    return raw


def main() -> None:
    tag, overrides = sys.argv[1], sys.argv[2:]
    seq = SEQUENCE
    pairs = [o.split("=", 1) for o in overrides]
    for k, v in pairs:
        if k == "seq":
            seq = " ".join(v.split("_"))  # underscores stand in for spaces on the command line
        elif k == "scramble":
            n, seed = (int(x) for x in v.split(":"))
            sc = random_scramble(n, seed)
            seq = to_string(sc + invert(sc))
    kw = {k: _coerce(k, v) for k, v in pairs if k not in ("seq", "scramble")}
    res = run_sequence(M1Params(**kw), parse(seq))
    res.update({"experiment": "E1-0", "scored": False, "tag": tag, "overrides": kw, "environment": environment()})
    out = Path(__file__).parent / "results" / f"{tag}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, indent=1, default=list))
    print(f"{tag}: completed {res['moves_completed']}/{len(parse(seq))} all_match={res['all_match']} "
          f"wall={res['wall_time_s']:.1f}s sim={res['sim_time_s']:.1f}s")
    for r in res["per_move"]:
        print("  ", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()
                     if k in ("move", "target_layer_rotation_deg_mean", "opposite_layer_rotation_deg_max",
                              "oracle_match", "max_turner_torque_Nm", "max_penetration_mm", "turn_error_deg")})


if __name__ == "__main__":
    main()
