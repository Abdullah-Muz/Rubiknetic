# D25: a faster magnet force callback? (UNSCORED feasibility study; pilot seeds 29001–29506; 2026-11-28)

**Why:** in the G1 cube-only rig the Python magnet callback (`MagnetSystem.apply`, run by `mujoco.set_mjcb_passive`
at every 0.5 ms step) is most of the step time, and in the two-arm G2 scene it is a sizeable share. A Python callback
also serialises `mujoco.batch.Batch`. The question: can it be made faster **without changing its results**?

**Scope:** measurement and a separate prototype only. Nothing in `src/rubiknetic/` or in G1/G2's frozen paths is
edited; the prototype lives in this folder and is put in place by an in-process monkeypatch (`ms.apply = ...`). It is
**not adopted** for any scored run. No package was installed.

**Scripts** (run from the repo root in WSL with `~/.venvs/rubiknetic/bin/python`; one simulation process at a time):

| Script | What it does | Output |
|---|---|---|
| `scenes.py` | Builds the G1 M7 rig through G1's own runner chain (`E7_scored_m7/run.py` loaded unchanged, as D20) and the two-arm scene through `E8_scored_g2/trials.py` (as D19); seed 29001. A `patch` hook swaps the callback before the first step. | — |
| `profile_apply.py g1\|two_arm` | Full step with / without / with an empty Python callback; per-stage timing of `apply` on 300 recorded poses (with a timer-instrumented verbatim copy of `pair_forces`, checked equal to the original); cProfile. | `results/profile_*.json`, `.log` |
| `fast_magnets.py` | The prototype (`FastApply`), option (a). | — |
| `equivalence.py` | Spline bit-identity test; 600 random poses of the M7 cube, original vs every prototype variant, bit for bit; C-port arithmetic checks. No simulation step. | `results/equivalence_poses.json` |
| `trajectory_bench.py g1\|two_arm` | Full trajectories per variant (from scratch), final qpos/qvel SHA-256 and divergence; interleaved timing. | `results/trajectory_bench_*.json`, `.log` |
| — | Key numbers of all of the above | `results/summary.json` |

**Machine caveat (applies to every timing here):** WSL, 16 logical CPUs, load average 12–14 from other users' jobs
during all runs. Absolute times are inflated (2–3x between best and median of the same block); the **ratios** of
interleaved blocks are the meaningful numbers. Timing medians of 3–5 interleaved blocks.

## 1. Profile: where `apply` spends its time (`FACT`, `results/profile_*.json`)

Per-stage time per callback (µs, mean over 300 recorded poses, offline, same data):

| Stage | G1 rig (U turn) | Two-arm scene |
|---|---|---|
| `world()` (body poses → magnet poses) | 128 | 170 |
| Neighbour-list check (`_update_list`) | 116 | 98 |
| Dipole terms, all list pairs (~185) incl. far taper and 2 cross products | **1,269** | **1,268** |
| Near-pair geometry (~22–24 near pairs) | 386 | 361 |
| Spline evaluation: 12 `RectBivariateSpline.ev` calls | 389 | 504 |
| Near-pair force / torque assembly | **804** | **793** |
| Per-magnet sums (one-hot matrix products, OpenBLAS) | 159 | 180 |
| Per-body sums + lever-arm cross product | 153 | 143 |
| `mj_applyFT` loop (20 bodies) | 266 | 339 |
| **Total** | **3,669** | **3,856** |

Full step (µs, median of 3 interleaved blocks of 400 steps):

| Scene | Original callback | No callback | Empty Python callback | Callback share |
|---|---|---|---|---|
| G1 rig (nv 84, NoSlip 10) | 5,119 | 1,569 | 1,567 | **69 %** |
| Two-arm (nv 99) | 18,410 | 13,181 | 12,423 | **28 %** |

- `FACT`: an *empty* Python callback costs nothing measurable: the cost is the work inside `apply`, not MuJoCo
  calling into Python.
- `FACT`: cProfile counts about **450 Python-level function calls per evaluation**; scipy's `pardeu` (8 of the 12
  spline calls) recomputes the derivative coefficients of the whole 73×31 table for every point.
- `INFERENCE`: the arithmetic itself is small (about 185 pairs × ~150 flops plus ~24 near pairs × 12 spline
  evaluations: some 50 k flops, tens of µs compiled). The callback is **dominated by per-call NumPy/SciPy overhead on
  ~180-element arrays** (an isolated NumPy op costs 1–16 µs here; there are ~150 of them), so a pure-NumPy rewrite
  can only remove a fraction; large gains need compiled code.
- The two-arm share (28 %) is higher than D19's 16–20 % because the machine was more loaded; the step itself is
  dominated by NoSlip (D19).

## 2. Options and their feasibility here

| Option | Feasible now? | Evidence |
|---|---|---|
| (a) Pure NumPy: fewer calls, no SciPy wrapper, precomputed spline coefficients | **Yes** (prototyped) | §3 |
| (b) Numba | **No** — not installed in `~/.venvs/rubiknetic` (a numba 0.68.1 / llvmlite 0.50.0 wheel sits in the uv cache; not used, per instructions) | `pip`-free listing of site-packages |
| (c) C MuJoCo engine plugin (`mjPLUGIN_PASSIVE`) | **No compiler**: WSL has binutils (`as`, `ld`) but no `gcc`/`cc`/`clang`/`cmake`/`make`; none found on Windows either | `which`, `/usr/bin` listing |
| (d) C callback via ctypes (`mujoco.set_mjcb_passive(ctypes_fn)`) | Same: needs a C compiler | as (c) |

**What (c)/(d) would need (not installed; for the user to decide):** a C compiler in WSL, e.g.
`sudo apt install gcc libc6-dev` (or `build-essential`). Headers are already shipped:
`site-packages/mujoco/include/mujoco/` (`mjplugin.h`, `mujoco.h`), and `libmujoco.so.4.0.1` is in the package.

`FACT` (MuJoCo 4.0.1 shipped headers and docs):
- `mjplugin.h`: `mjpPlugin` with `capabilityflags` including `mjPLUGIN_PASSIVE = 1<<2` ("passive forces"), callbacks
  `nstate`, `init`, `destroy`, `copy`, `reset`, `compute(m, d, instance, capability_bit)`; registered with
  `mjp_registerPlugin` (library constructor `mjPLUGIN_LIB_INIT`), loaded with `mj_loadPluginLibrary`; per-instance
  state in `d->plugin_state` (`npluginstate`) and `d->plugin_data`. A plugin instance must be declared in the model
  (MJCF `<extension>/<plugin>`), so the scene XML changes.
- `doc/python.rst`: a `mjcb_*` set to a ctypes function pointer to a native function is assigned directly to the raw
  callback pointer and "the GIL will **not** be acquired".
- `batch.py` / `doc/python.rst`: in `mujoco.batch.Batch`, physics callbacks "must be C functions, installed through
  ctypes: a Python function installed as one makes the batch's calls raise ValueError"; a ctypes wrapper of a Python
  function is accepted but "holds the Global Interpreter Lock while it runs, which serializes the batch's threads";
  "engine plugins that keep state outside plugin_state share it among the simulations a thread runs, unless the batch
  is persistent". Batch results are "bit-identical to a loop over one MjData per simulation at any thread count".

## 3. Prototype (option (a)) and results

`FastApply` ("tuned") reproduces `apply` with the same floating-point operations in the same order and fewer Python
calls: SciPy's compiled `bispeu`/`pardeu` called directly (no `RectBivariateSpline.ev` wrapper), the C2 taper with
each power computed once, `np.linalg.norm`/`np.sum`/`np.einsum` replaced by the numpy calls they run internally
(`sqrt(add.reduce(x*x))`, `add.reduce`, `c_einsum`), and the original neighbour list, stats, `last` record and
`mj_applyFT` accumulation of the wrapped object (so shared state, e.g. `MagnetMonitor.energy()` calls between steps,
evolves exactly as before). Variants tried and rejected on speed (measured in isolation): an index-array cross product
(25 vs 21 µs), a vectorised NumPy re-implementation of FITPACK ("fused", 741 vs 239 µs — 3x slower, kept only for the
bit-identity test), `np.bincount` per-magnet sums (48 vs 35 µs, and not bit-identical, below).

### 3.1 Equivalence (`FACT`)

**Random poses** (`results/equivalence_poses.json`; the M7 cube model, 300 large random poses — random layer turns
and up to 3° per-cubie tilts, neighbour list rebuilt at every call — and 300 small steps with the list kept;
qfrc = the generalized force the callback adds, 84 values per call):

| Variant | qfrc values bit-equal | F, T per magnet | Energy U | Stats |
|---|---|---|---|---|
| **tuned** (direct spline, BLAS sums) | **50,400 / 50,400** | identical | 600/600 | identical |
| numpy changes only (scipy `.ev`) | 50,400 / 50,400 | identical | 600/600 | identical |
| fused FITPACK re-implementation | 50,400 / 50,400 | identical | 600/600 | identical |
| sequential per-magnet sums (`bincount`) | 38,324 / 50,400 | max rel. 3.3e-13 | — | `max_force_N` differs in last bits |
| "perturbed" (sequential magnet and body sums) | 36,331 / 50,400 | max rel. 3.3e-13 | — | as above |

**Spline:** the vectorised FITPACK re-implementation (de Boor–Cox basis in FITPACK's order, derivative coefficients
precomputed with `parder`'s formula, degree-2 derivative basis taken from the degree-3 recursion) reproduces SciPy
1.18.1's `ev` (value, ∂ρ, ∂z) for all four M7 tables **bit for bit** at 20,755 points per table and derivative including ρ = 0, every knot
and the domain edges.

**Trajectories** (`results/trajectory_bench_*.json`; each variant built from scratch with its callback before the
first step):

| Scene, trajectory | Variant | Final qpos/qvel SHA-256 vs original | Divergence |
|---|---|---|---|
| G1 rig: 0.5 s settle + U turn, **5,364 steps** | tuned | **identical** (all 43 checkpoints, every 100 steps of the turn) | none |
| | original again (control) | identical | none |
| | perturbed (≈1e-13 relative force differences) | different | already at the first checkpoint (step 1,100); final max \|Δqpos\| **1.5e-3** |
| Two-arm: start sequence (7,200) + 2,000 control steps, **9,200 steps** | tuned | **identical** (all 20 checkpoints of the 2,000 steps) | none |
| | original again (control) | identical | none |
| | perturbed | different | already at the first checkpoint; final max |Δqpos| **2.8e-4**; validity stats still clean (max near tilt 1.59° vs 1.60°) |

### 3.2 Speed (`FACT`, interleaved blocks of 300 steps in one scene, 5 rounds, medians)

| Scene | Callback alone: original → tuned | Full step: original → tuned | Full step with no callback (bound) |
|---|---|---|---|
| G1 rig | 2,656 → 2,107 µs (**1.26x**) | 5,552 → 4,592 µs (**1.21x**) | 1,690 µs (3.3x) |
| Two-arm | 1,714 → 1,392 µs (**1.23x**) | 8,734 → 8,010 µs (**1.09x**) | 6,171 µs (1.42x) |

The machine load fell during the two-arm timing (8.7 ms per step here vs 18.4 ms in the §1 profile run), so the two
tables' absolute numbers are not comparable; within each table the blocks are interleaved.

## 4. Reading

- `FACT`: the tuned pure-NumPy callback is **bit-identical** to the original on 600 random poses and on full
  trajectories in both scenes (G1 U turn, 5,364 steps; two-arm start sequence + 2,000 steps, 9,200 steps: same
  final qpos/qvel SHA-256, same magnet stats), and **~1.23–1.26x faster as a callback**; the full step gains ~1.2x
  (G1) and ~1.09x (two-arm). It changes no arithmetic, but the gain is small.
- `FACT`: removing the callback cost entirely would make the G1 rig step **3.3x** and the two-arm step **1.4x**
  faster; a compiled callback would approach those bounds (`INFERENCE`: tens of µs per call vs 1.4–2.7 ms).
- `FACT`: **a compiled port cannot be bit-identical to the current Python callback** with ordinary C code:
  1. numpy's float64 power (`r**3`, `r**4`, `t**3..t**5`) differs from the C library `pow` by 1 ulp in **~5.4 %** of
     values on this machine (numpy dispatches to its own SIMD code);
  2. the per-magnet sums are OpenBLAS one-hot matrix products whose summation order is not sequential (sequential
     sums differ by up to 3e-13 relative); it is the SkylakeX kernel chosen at run time (`DYNAMIC_ARCH`).
  The FITPACK spline itself *can* be reproduced exactly (shown above).
- `FACT`: rounding-level force differences are **not** harmless at the trajectory level: in the G1 rig they grow to
  1.5e-3 in qpos within one U turn and to 2.8e-4 over the two-arm trajectory (the contact/NoSlip dynamics amplify
  them). So a C port — or even the current code
  on a CPU where OpenBLAS picks another kernel — gives different individual trajectories.
- `INFERENCE`: the current scored results are therefore bit-reproducible only on the same CPU family / library
  versions; a C port needs its own **statistical equivalence validation** (pre-registered: same trial batteries,
  outcome rates and validity diagnostics compared with the Python reference, plus a per-step force comparison at
  ~1e-12 relative) before use in any scored run. It is not a drop-in.

## 5. Could `mujoco.batch.Batch` / `mujoco.rollout` then be used? (`INFERENCE` unless marked)

With a C magnet force, the magnet law no longer blocks Batch, but the harness still would:
1. **Neighbour-list state.** The Verlet list is history-dependent (p_ref) and changes the summation order. For Batch
   (non-persistent by default) it must live in the state row: e.g. the 48×3 reference positions in `plugin_state`
   (plugin) or `userdata` (callback; needs `nuserdata` in the model). The list itself can be rebuilt from p_ref.
   Diagnostics (max near tilt, near-perpendicular, clamped z; G1 rule 2 / G2 validity) must be accumulated there too.
2. **Python controllers at every physics step.** G2's `TwoArm.ctrl_step` runs `impedance()` and `j7_control()` in
   Python before every 0.5 ms step; G1's `TurnRig` sets controls per step. Batch can only run several steps per call
   with fixed controls, so these laws would need to become MuJoCo actuators or a C `mjcb_control`, or a policy step
   per physics step (no parallel gain).
3. **AuditedSim.** The per-step edit audit and monitor hooks (`Monitor`, `MagnetMonitor` reading `_buf` and `last`
   after every step) are Python per step. Inside a Batch call nothing can edit state, so the audit could move to
   call boundaries, but that changes the scored harness (a decision for the user).
4. `mujoco.rollout` (`FACT`: its signature takes open-loop `control` sequences) fits only open-loop segments.
- `INFERENCE`: process-level parallelism (G2 already runs 8 workers) works with the Python callback today. The main
  wins from a C callback are per-process: up to ~3.3x for the cube-only rig, up to ~1.4x for the two-arm scene (NoSlip
  dominates there, D19).

## 6. What adoption would require

- **Tuned NumPy (bit-identical):** a code-review of `fast_magnets.py`, the equivalence tests here turned into unit
  tests, and a decision record (new P-number) — no physics re-validation, since bits are unchanged; gain ~1.1–1.2x per step. Must
  not be applied to G1/G2's frozen runs.
- **C callback / plugin:** user approval to install a compiler; a C port with the FITPACK evaluation copied exactly;
  state in `plugin_state`/`userdata`; then a pre-registered equivalence study vs the Python reference (per-step force
  agreement and statistical agreement of trial outcomes), recorded in `docs/DECISION_LOG.md`, before any scored use.

## Limitations

- Timings on a heavily shared machine; ratios only. One seed (29001) per scene; one turn (G1) and 2,000 steps
  (two-arm). Composite magnet systems (P-67) are not supported by the prototype (asserted).
- The large random poses include unphysical overlaps (forces up to 1.6e9 N); they test arithmetic identity only.
- Bit-identity is shown for this machine and these library versions (numpy 2.5.4, scipy 1.18.1, OpenBLAS 0.3.34
  SkylakeX kernel, MuJoCo 4.0.1).
