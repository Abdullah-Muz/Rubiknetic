"""ER1 probe 1 variant: probe_slip with the setup misalignment replaced (zero | U_only), as in probe 3.
Usage: er1_probe_slip_variant.py <variant> <seed> <times...>; writes results/probe_slip_<variant>_s<seed>.json."""
import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import er1_probe_slip as P  # noqa: E402

variant, seed, times = sys.argv[1], int(sys.argv[2]), [float(x) for x in sys.argv[3:]]
M5 = P.D10._load_m5()
from rubiknetic.cube_physics import scored  # noqa: E402
orig = scored.draw_setup


def patched(s, *a, **k):
    st = orig(s, *a, **k)
    mis = {f: 0.0 for f in st.misalign_deg}
    if variant == "U_only":
        mis["U"] = st.misalign_deg["U"]
    return dataclasses.replace(st, misalign_deg=mis)


scored.draw_setup = patched
P.main(seed, times)
src = HERE / "results" / f"probe_slip_s{seed}.json"
dst = HERE / "results" / f"probe_slip_{variant}_s{seed}.json"
src.replace(dst)
print("->", dst.name)
