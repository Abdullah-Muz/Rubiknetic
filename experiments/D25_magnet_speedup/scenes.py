"""D25 (UNSCORED): build the two benchmark scenes in-process, read-only, with pilot seeds (29xxx).

* g1_scene(seed): the G1 M7 cube-only rig (rounded edges 2.5 mm, NoSlip 10, 48 x 4x2 mm N35 magnets, B1, gap 0.05 mm),
  built through G1's own scored runner chain (experiments/E7_scored_m7/run.py loaded unchanged, as D20 did): E7.install,
  M4.use_magnets and scored.Trial (0.5 s settle). Returns (trial, magnet system).
* two_arm(seed, patch): the G2 two-arm scene (experiments/E8_scored_g2/trials.py loaded unchanged, as D19 did); the
  TwoArm constructor runs the start sequence. `patch(ms)` (optional) is called on the MagnetSystem right after
  hold.install_magnets builds it, before any step, so a replacement callback can be put in place for the whole trial.
Nothing here writes into the repository or changes a frozen file; the monkeypatches live only in this process."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))


def _exec(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def g1_modules():
    E7 = _exec("e7_run", REPO / "experiments/E7_scored_m7/run.py")
    from rubiknetic.cube_physics import scored
    return E7, scored


def g1_scene(seed: int = 29001, patch=None):
    """The G1 M7 rig after Trial's 0.5 s settle. patch(ms) is applied before the Trial is built (so before any step)."""
    assert 29000 <= seed <= 29999, "pilot seeds only"
    E7, scored = g1_modules()
    M4, R = E7.M4, E7.R
    E7.install(E7.EDGE_R, E7.NOSLIP)
    M4.configure_process()
    mp = R.magnet_params_for({})
    ms = M4.use_magnets(mp, R.GAP)
    ms.reset_neighbour_list()
    ms.reset_stats()
    if "apply" in ms.__dict__:
        del ms.apply                         # undo a previous patch on the process-wide magnet system
    if patch is not None:
        patch(ms)
    setup = scored.draw_setup(seed)
    tr = scored.Trial(scored.params_for(setup), setup)
    return tr, ms


def g1_move(text: str):
    from rubiknetic.cube_logic import parse
    return parse(text)


def two_arm_modules():
    T = _exec("trials", REPO / "experiments/E8_scored_g2/trials.py")
    return T


def two_arm(seed: int = 29001, patch=None):
    assert 29000 <= seed <= 29999, "pilot seeds only"
    T = two_arm_modules()
    H = T.TA.H
    if not hasattr(H, "_d25_orig_install"):
        H._d25_orig_install = H.install_magnets

    def install(m, p):
        ms = H._d25_orig_install(m, p)
        if patch is not None:
            patch(ms)
        return ms

    H.install_magnets = install
    T.reset_phase()
    T.configure({}, T.start_draw(seed))
    r = T.TA.TwoArm(T.L, T.HC, T.DEFAULTS["grip"])
    return r, T
