# P2 robot model — xArm7 + Gripper G2 in MuJoCo (UNSCORED prototype)

**Date:** 2026-11-13 · **Status:** unscored Phase 2 prototype; sanity/smoke tests only. **No G2 gate criterion is claimed**, nothing here is a `VALIDATED_RESULT`.
**Decision context:** DECISION_LOG P-17 (Gripper G2 confirmed; xArm7 URDF peak efforts accepted as working torque limits; **xArm7 hardware revision pending**, so both revisions are built, default `1305+`). Source research: `docs/research/PHASE_2_ROBOT_MODEL_FINDINGS.md` (RM-01…RM-10). **Revision 2 (same day):** user-approved changes (a)–(d) below, relayed by the coordinator; the DECISION_LOG has not been edited by this experiment.
**Tags:** `FACT` (read in a cited source or measured by the scripts here, one run), `INFERENCE`, `ASSUMPTION`, `PROPOSAL`.

## 1. What was built

| File (repo, new) | Purpose | Runs in |
|---|---|---|
| `convert_g2_meshes.py` | G2 `.dae` → STL; checks the loader on the G1 `.dae`/`.stl` pairs first | `~/.venvs/cadtools` (trimesh 5.2.1, pycollada 0.9.3), `python -I` |
| `build_model.py` | Generates the MJCF from the third-party assets; `--revision 1305+|pre-1305`, `--no-gravcomp`, `--grip-force N`, `--clip-1305-spec-limits`; gripper calibration; `set_grip_force()` helper | project venv (MuJoCo 4.0.1) |
| `test_model.py` | Sanity tests T1–T5 → `results/test_results.json` | project venv |
| `measure_g2_step.py` | Measures the official G2 STEP (fingertips, fasteners, mount) from cascadio GLB conversions (`cascadio.step_to_glb(src, out, tol_linear=0.05, tol_angular=0.3)`, ≈ 3 min each) | cadtools venv (cascadio 0.1.1), `python -I` |
| `integration_hold_m2.py` | **Exploratory, unscored** integration: xArm7 + G2 holding the M2 cube (§4) → `results/integration_hold_m2.json` | project venv |

Third-party inputs and all generated models/meshes live in the git-ignored `third_party_cad/robot/` (see its `SOURCES.md`; licences beside each source). Nothing third-party is vendored into the repo.

Reproduce:
```bash
~/.venvs/cadtools/bin/python -I experiments/P2_robot_model/convert_g2_meshes.py
UV_PROJECT_ENVIRONMENT=$HOME/.venvs/rubiknetic $HOME/.local/bin/uv run python experiments/P2_robot_model/test_model.py          # builds all variants
UV_PROJECT_ENVIRONMENT=$HOME/.venvs/rubiknetic $HOME/.local/bin/uv run python experiments/P2_robot_model/integration_hold_m2.py
```

### Model contents (generated `third_party_cad/robot/generated/xarm7_g2_<rev>[_nogc][_clip].xml`)

Starts from Menagerie `ufactory_xarm7/xarm7.xml` (arm + original-gripper MJCF) and changes:

| # | Change | Tag / source |
|---|---|---|
| 1 | Arm actuator `forcerange` **and** joint `actuatorfrcrange` = URDF `max_effort`: `1305+` 179.4445/179.4445/92/92/81.558/30.6/30.6 N·m; `pre-1305` 163.2/163.2/81.6/81.6/81.6/30.6/30.6 N·m (Menagerie had 50/50/30/30/30/20/20). Checked against the YAML text at every build | `FACT` xarm_ros2 `config/xarm7/joint_limits{,_1305}.yaml`; peak/overload values, accepted as working limits by the user (P-17) |
| 2 | `1305+`: arm visual = `meshes/xarm7_1305/visual/*.stl`, collision = separate `collision/*.obj`. `pre-1305`: Menagerie STLs, visual used as collision | `FACT` URDF mesh selection for `model_num ≥ 1305`; same link frames (bounds checked) |
| 3 | Gravity compensation (default on): `gravcomp=1` on link1–7 and the gripper base; `actuatorgravcomp="true"` on joints 1–7, so the compensation is **actuator torque**, summed with the servo and clamped by `actuatorfrcrange`. Not applied to the 6 finger/knuckle bodies (0.21 kg). No `xfrc_applied`/`qfrc_applied` writes | `PROPOSAL`; MuJoCo attributes. `ASSUMPTION`: exact model masses |
| 4 | Gripper meshes = converted G2 meshes. `FACT` (measured): only `base_link_g2` differs from G1; the six knuckle/finger G2 meshes are vertex-identical to G1 (Hausdorff ≤ 0.0001 mm). `base_link_g2.dae` has 159 zero-area fragments 0.5 m away (export artefact), removed (0.066 mm²) | `convert_g2_meshes.py` |
| 5 | Gripper joints, joint origins and inertials kept from the original gripper | `FACT` `xarm_gripper.urdf.xacro`: `gripper_version:=G2` only switches mesh filenames |
| 6 | Gripper attach quaternion = identity (URDF); Menagerie used `0 0 0 1` | `FACT` URDF; `INFERENCE`: only swaps left/right |
| 7 | Gripper joints `frictionloss` 0 (Menagerie class default gave them the arm's 1 N·m) | `ASSUMPTION`: URDF gripper joints have no `<dynamics>` |
| 8 | Gripper actuator (tendon `split` = driver angle θ): `ctrl` = θ target. Tendon force limit f = F·k − τ_spring, k = \|dd/dθ\| at d = 57 mm = **0.10285 N·m per N** (virtual work), F = grip setting 10–50 N; kp 102.9, kv 2.571 (saturated free closing ≈ URDF 2 rad/s) | `FACT` G2 10–50 N (UM v2.7.1); gains `PROPOSAL`; 57 mm `ASSUMPTION` |
| **(a)** | **Open gap limited to 85 mm**: drive-joint lower limit and `ctrlrange` low = θ_open = **0.0458 rad** (keyframe updated). **Distal pad (`pad_2`) extended 3 mm toward the fingertip** (half-height 9.5 → 11 mm, centre +1.5 mm) | `FACT` 85 mm from the G2 drawing (UM v2.7.1 §6.2); 3 mm from the STEP comparison (§3); user-approved |
| **(b)** | **Linkage-spring offset calibrated out**: τ_spring = Σ stiffness·(springref − θ₅₇) over the two inner-knuckle joints, read from the compiled model = **0.2282 N·m ≙ 2.22 N**, subtracted from the tendon force limit (`set_grip_force`) | user-approved; spring values `FACT` (Menagerie) |
| **(c)** | **`--clip-1305-spec-limits`** (1305+ only, **off by default**): J2 −117…116°, J4 −6…225° on joint range and actuator `ctrlrange`; default keeps the URDF ranges (J2 −118…120°, J4 −11…225°) | `FACT` RM-05/RM-07; user-approved as a flag until the revision is confirmed |
| 9 | Sites `left/right_pad_center` (measurement only) | — |

Kept from Menagerie unchanged (`FACT`): inertials (= `xarm7_type7_HT_BR2`), servo kp/kv (1500/150, 1000/100, 800/80), arm joint damping/armature/frictionloss, pad boxes otherwise (30 × 4 mm section, friction 0.7/0.6), four-bar closure (2 `connect` + 1 joint equality), timestep 0.002 s, `implicitfast`.

## 2. Test results (revision 2; one run 2026-11-13 ~21:57 PST; WSL2 Ubuntu 24.04, 16 logical CPUs, 1 thread; MuJoCo 4.0.1, numpy 2.5.4, Python 3.12.3)

**T1 load** — all variants compile (`1305+`, `pre-1305`, each ± gravcomp, plus `1305+_clip`). nq = nv = 13, nu = 8, nbody 16, neq 3; ngeom 27 (`1305+`) / 19 (`pre-1305`). Total mass 12.07 kg (gripper 0.751 kg); 0 contacts at `home`. `_clip`: J2 and act2 [−117, 116]°, J4 and act4 [−6, 225]° ✓.

**T2 hold under gravity, 4 s position control** (max joint deviation from the commanded pose; unchanged by revision 2):

| Variant | `home` sag | `reach` sag | Peak joint torque / limit |
|---|---|---|---|
| servo only (`_nogc`) | 0.0154 rad (J4) | 0.0140 rad (J2) | 0.12–0.19 |
| servo + actuator gravcomp | **0.00086 rad (J4)** | **0.00050 rad (J2)** | 0.12–0.19 |

Same for both revisions. `qfrc_passive` on arm joints = 0 (gravcomp routed through actuators); `xfrc_applied`/`qfrc_applied` stayed exactly 0; all states finite. `INFERENCE`: the residual comes from the uncompensated finger bodies (≈ 0.4 mm at the TCP).

**T3 gripper stroke (free space)** — open 84.73 mm (target 85; the ≈ 0.3 mm shortfall is linkage/constraint compliance) → closed 1.64 mm: **stroke 83.1 mm vs 84 ± 1 mm ✓** (before (a): 87.0 mm). 10–90 % closing 0.23 s. **Pad span vs STEP at the STEP pose (29.16 mm gap): pads 136.31…176.31 mm from the flange face vs STEP fingertip 136.3…176.3 mm; pad face \|y\| 14.58 mm vs 14.58 mm ✓.**

**T4 squeeze a static 57 mm box** (gripper commanded fully closed, arm holding `home`):

| Setting | Left / right pad N | Error vs set-point | Before (b) | Other box contacts | Penetration |
|---|---|---|---|---|---|
| 10 N | 10.32 / 10.32 | **+0.32 N** | +2.44 N | none | 0.001 mm |
| 30 N | 29.97 / 29.97 | **−0.03 N** | +2.18 N | none | 0.003 mm |
| 50 N | 49.84 / 49.84 | **−0.16 N** | +2.05 N | none | 0.005 mm |

`INFERENCE`: the remaining ±0.3 N trend comes from the final gap growing with force (57.05 → 57.27 mm; soft four-bar constraints), which changes k and the spring term slightly.

**T5 throughput** (single thread): this run hold 3 500–7 700 steps/s, squeeze 2 700–3 900 steps/s. The first run (§ history) gave 9 400–19 100 / 10 200–16 000 on the same code path; the machine was evidently loaded during this run (other work was running). Treat as order of magnitude only.

## 3. G2 STEP measurements (official CAD; use authorised by the user 2026-11-13)

Inputs: `Gripper G2 AG1200 20250710.STEP` (with fingers) and `… -Without Fingers 20250721.STEP` (URLs, SHA-256 in `third_party_cad/robot/SOURCES.md`). Tessellated with cascadio (0.05 mm) and measured by `measure_g2_step.py`; raw output `third_party_cad/robot/g2_step_derived/step_measurements.json` (git-ignored). **No STEP geometry is used in the MJCF**; only the two numbers in (a) (85 mm is from the drawing; the 3 mm pad extension is from this comparison) are informed by it. `FACT` = measured on the tessellation, ±~0.1 mm; interpretation `INFERENCE`. Frame: x = opening, y = thickness, z = along the gripper axis.

| Quantity | Value (from STEP) |
|---|---|
| Overall envelope at the modelled pose | 130.9 (x) × 75.0 (y, = Ø75 flange) × 181.3 mm (z, from the lowest point) |
| Base: 5 mm boss (r ≤ 28 mm) below the Ø75 flange face | `INFERENCE`: the manual's L is measured from the flange face (z = 5 mm here); then the tip end is at L = 176.3 mm, and the manual formula gives L(d = 29.16) = 176.3 mm ✓. The URDF `base_link_g2` mesh spans z −5…104.8 mm, i.e. its origin is the flange face ✓ |
| STEP pose | partly closed: pad-face gap 29.16 mm (single pose; no stroke information) |
| Removable fingertip, per side | plate 5.0 × 32.0 × 40.0 mm + inner pad layer 3.0 × 29.5 × 37.5 mm; gripping face at \|x\| = 14.58 mm; spans z = 136.3…176.3 mm from the flange face |
| Finger-mount face | \|x\| = 21.58 mm (plate outer face); finger wall to \|x\| = 25.56 mm (≈ 4 mm) |
| Fasteners, per side | 2 screws from the outside of the finger; head Ø ≈ 5.5 mm, 2.0 mm proud; shank end face Ø 3.0 mm; on the finger centreline; 12.0 mm pitch at 146.3 and 158.3 mm from the flange face |
| Thread / depth | not modelled in the CAD. Screw ends at \|x\| = 18.6 mm, 3.0 mm into the 5 mm plate → `INFERENCE`: blind tapped M3, ≈ 3 mm engagement |

**(d) Fingertip mount — PROVISIONAL:** 2 × M3 (inferred from Ø3.0 shank / Ø5.5 head), 12.0 mm pitch on the finger centreline, ≈ 3 mm thread engagement in a 5 mm plate, fingertip envelope 32 × 40 mm. **To be confirmed with calipers on the real gripper before any fingertip is manufactured** (thread size, pitch, hole depth, mount-face flatness, locating features). The earlier "finger width 16 mm" reading of the manual side view conflicts with the STEP's 32 mm; `INFERENCE`: a half-width.

## 4. Exploratory, UNSCORED integration test: one xArm7 + G2 holding the M2 cube

**Not Phase 2 work; G1 is not signed off.** `integration_hold_m2.py`, runs 2026-11-13 22:22 and 22:25 PST (the second adds the slip time series; all physical results identical). The steps/s column below is from the first run.

Setup (`FACT` unless tagged):
- **Cube:** `experiments/M2_switched_welds/m2_model.build_m2_xml` and `switching.py` imported **unchanged**, `M1Params(radial_preload=0.0, rig=False)`. Free core added exactly as in `D6_free_core/run_stab.py` (freejoint + 1.7 g core inertial); the core body's `pos`/`quat` place it at the grasp point (initial condition). `rig=False` (deviation from run_stab): the Phase-1 turning rig is fixed at the world origin, is not needed (no turning) and would sit inside the robot base. Cube mass 90.1 g (weight 0.884 N).
- **Merge:** robot `1305+` (gravcomp on) as the MjSpec parent, the cube attached with its names unchanged; the cube's solver options copied to the parent (timestep 0.0005 s, Newton, elliptic cone, impratio 10). 43 bodies, nq 106, nv 85, 149 equalities.
- **Grip:** arm at `home` (gripper axis = world −z within 0.0004), pads on the R/L faces. Pad tip 2.5 mm beyond the D face → pads cover cube z −30.9…+9.1 mm, i.e. **D and E layers only** (U layer starts at +9.5 mm). Pad contact: G2 pads (condim 3, μ 0.7/0.6) on cubies.
- **Procedure:** setup (t < 0, diagnostic, as in run_stab): gravity off for 2.0 s while the gripper position target ramps from open to closed at 0.5 rad/s (≈ 26 mm/s per pad; `PROPOSAL`), then gravity on and a **3 s hold**. Runs through `SwitchAuditedSim` + `SwitchManager` (any state edit raises; switches are logged).
- **Hold criterion (`PROPOSAL`, unscored):** core slip relative to the gripper < 1 mm and rotation < 1° over 3 s, pads on D/E only, no audit violation or numerical failure.

Results:

| Grip setting | Holds | Core slip (max) | Core rotation | Pad normal N (L/R, last 0.5 s) | Tangential N per pad | Friction use (max, of μ = 0.7) | Layers touched | Max penetration | Cubie lattice deviation | Switch events | steps/s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 N | **yes** | 0.093 mm | 0.007° | 10.48 / 10.48 | 0.44 | 7.3 % | D, E | 0.074 mm | 0.0025 mm / 0.008° | none | 840 |
| 30 N | **yes** | 0.089 mm | 0.001° | 30.43 / 30.43 | 0.44 | 2.2 % | D, E | 0.19 mm | 0.0032 mm / 0.010° | none | 820 |
| 50 N | **yes** | 0.065 mm | 0.001° | 50.38 / 50.38 | 0.44 | 1.3 % | D, E | 0.29 mm | 0.0039 mm / 0.012° | none | 786 |

No non-pad robot geometry touched the cube; no audit violations; no numerical failures. Tangential force per pad ≈ weight / 2 (0.442 N) ✓. Penetration grows with grip force (0.07 → 0.29 mm; contact softness, M1 cubie `solref` 0.001).

**The core slip is a slow, steady creep, not settling** (second run, deterministic, identical end values; slip in mm at t = 0.05 / 0.5 / 1 / 2 / 3 s): 10 N 0.013 / 0.045 / 0.053 / 0.072 / 0.093; 30 N 0.022 / 0.037 / 0.051 / 0.069 / 0.089; 50 N 0.013 / 0.012 / 0.025 / 0.045 / 0.065. Rate ≈ **0.02 mm/s at every grip force**, although friction use is only 1–7 %. `INFERENCE`: this is the known creep of MuJoCo's soft (compliant) friction constraints under a sustained tangential load, not Coulomb slip; it would extrapolate to ≈ 1.2 mm/min. It passes the 3 s criterion, but a long hold (e.g. a full solve) would accumulate millimetres. `PROPOSAL`: test stiffer pad `solref`/higher `impratio`, or a feedback re-grasp, before relying on long holds.

Throughput (single thread, dt 0.5 ms): 786–840 steps/s (first run), 408–593 steps/s (second run, machine loaded) — ≈ 0.2–0.4× real time.

**Negative result (preserved): first attempt failed.** With a *step* close command and a 0.5 s setup: at 10 N the pads reached the cube only at the moment gravity returned (75 N impact spike, cube dropped); at 30 N the impact bounced the floating cube out of the grip (dropped); at 50 N it held but shifted ≈ 5 mm toward the flange during the bounce, and 6 non-pad robot contacts and 1.38 mm penetration appeared. `INFERENCE`: grasping a free 90 g cube needs a speed-limited close (as the real G2's speed setting provides) and settling before load; the step response of the force-limited servo is too violent. The ramped close is a controller choice, not a model change.

**Limits:** gravity-off setup is a diagnostic shortcut (no approach motion is simulated); one pose, one cube orientation, no turning, no disturbance; G2 pads are Menagerie boxes (no torsional friction, condim 3); M2 shell stays welded (no layer unlock is requested since no turner acts); one run per setting.

## 5. Known gaps

1. Fingers/knuckles are G1 geometry (UFACTORY's G2 URDF reuses them); pads now match the STEP fingertip position and length but are Menagerie boxes. The project's custom fingertips (D-04) will replace them.
2. Mass: gripper 0.751 kg (URDF G1 inertials) vs G2 820 g / 800 g; arm+gripper 12.07 kg vs 14.3 kg (1305 manual). Inertials are not revision-specific.
3. No joint velocity/acceleration limits in MuJoCo; the controller must enforce 3.14 rad/s (arm) and the G2 15–225 mm/s.
4. Grip-force calibration is exact at 57 mm only (±0.3 N there); other widths not calibrated. Torque limits are peak/overload values.
5. Gravity compensation is ideal; contact parameters are Menagerie/M1 defaults, not identified.
6. One run per test, one machine; throughput numbers are noisy.

## 6. Decisions still needed (user)

- xArm7 hardware revision (`1305+` default vs `pre-1305`); then whether to turn on `--clip-1305-spec-limits`.
- Caliper confirmation of the fingertip mount (§3 (d)) before fingertip CAD/manufacture.
- Whether the ramped-close grasp procedure (§4) should become the default gripper command in the controller.
- Whether to investigate the ≈ 0.02 mm/s soft-contact creep (§4) before longer holds.
- Whether to vendor any third-party assets (BSD-3 meshes/MJCF) into the repo.

## 7. Sources (accessed 2026-11-13)

RM-01 Menagerie `ufactory_xarm7` (HEAD `370c4396…`), RM-03 `xarm_ros2` humble (`ac736c92…`), RM-05 spec page, RM-06 G2 User Manual v2.7.1, RM-07 HW manual v2.7.1, RM-04 UFACTORY download centre (G2 STEP zips); exact URLs, SHAs and hashes in `third_party_cad/robot/SOURCES.md`. MuJoCo XML reference for `gravcomp`, `actuatorgravcomp`, `actuatorfrcrange` (https://mujoco.readthedocs.io/en/stable/XMLreference.html; attributes verified by compiling a test model in MuJoCo 4.0.1). M2 cube: `experiments/M2_switched_welds/` (P-17), free core: `experiments/D6_free_core/run_stab.py`.
