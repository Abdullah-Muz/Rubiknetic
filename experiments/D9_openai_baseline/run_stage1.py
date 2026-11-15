"""D9: run the D8-1b stage-1 battery (unmodified test functions, seeds and oracle) on the OpenAI robogym cube.

NOT yet run (2026-11-14): only smoke.py has been executed. See PROTOCOL.md.
Usage (WSL): ~/.venvs/rubiknetic/bin/python experiments/D9_openai_baseline/run_stage1.py <A|B> [test ...]
Results: experiments/D9_openai_baseline/results/stage1/<A|B>/<test>.json (existing files are skipped).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "D8_alignment"))
import openai_cube as OC  # noqa: E402
import d8_1b_stage1 as S1  # noqa: E402


def main() -> None:
    variant = sys.argv[1]
    OC.install(variant)
    out = HERE / "results" / "stage1" / variant
    out.mkdir(parents=True, exist_ok=True)
    todo = S1.tests()
    for name in sys.argv[2:] or list(todo):
        if (out / f"{name}.json").exists():
            continue
        kind, kw = todo[name]
        load0 = os.getloadavg()[0]
        t = time.perf_counter()
        rec = S1.run(kind, kw)
        wall = time.perf_counter() - t
        dt = OC.VARIANTS[variant].get("timestep", 0.0005)
        steps = rec.get("sim_time_s", 0.0) / dt
        rec.update({"config": f"openai_{variant}", "solver_variant": variant, "solver_overrides": OC.VARIANTS[variant],
                    "geometry_overrides": OC.GEOM, "test": name, "kind": kind, "kwargs": kw, "wall_s": wall,
                    "steps_per_s": steps / wall if wall else None, "loadavg_start": load0,
                    "mujoco": mujoco.__version__})
        (out / f"{name}.json").write_text(json.dumps(rec, indent=1, default=str))
        summary = {k: rec.get(k) for k in ("pass", "moves_ok", "n_moves", "U_err_after_release_deg",
                                            "U_err_after_1s_deg", "outcome", "max_twist_deg", "aborted") if k in rec}
        print(f"[openai_{variant}] {name}: {summary} {rec['steps_per_s']:.0f} steps/s", flush=True)


if __name__ == "__main__":
    main()
