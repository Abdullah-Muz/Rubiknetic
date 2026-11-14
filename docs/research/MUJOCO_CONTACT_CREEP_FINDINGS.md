# MuJoCo static-friction creep: options, mechanism, costs (research only)

**Date:** 2026-11-13 · **Status:** desk research. **No simulation was run for this report** (a scored run was using the CPU). Nothing here is a `VALIDATED_RESULT`. The test plan in §6 is unscored and has not been run.
**Trigger:** `experiments/P2_robot_model/README.md` §4. In that test an xArm7 + G2 holds the 90 g M2 cube by friction, and the core creeps at about 0.02 mm/s at 10, 30 and 50 N grip, while using only 1–7 % of the friction cone.
**Tags:** `FACT` = read in a cited doc, source file or issue; `INFERENCE` = derived from facts, not tested; `ASSUMPTION`; `PROPOSAL`.
**MuJoCo version:** 4.0.1, the version pinned in the project venv. Source code was read at git tag `4.0.1`.

---

## 0. Correction to the settings in the brief (read this first)

The brief lists the pad contact as condim 4, μ 0.8, solref (1 ms, 1) and solimp (0.95, 0.99, 0.5 mm). **Those are the M1 turning-rig pad defaults** (`src/rubiknetic/cube_physics/m1_model.py`, `M1Params.pad_*`). They are **not** the G2 pads used in the integration test. `FACT`:

| Contact in `integration_hold_m2.py` | Source | Values |
|---|---|---|
| G2 pads `left/right_finger_pad_1/2` | `third_party_cad/robot/generated/xarm7_g2_1305+.xml`, classes `pad_box1/2` | `priority="1"`, friction 0.7 (pad_1) / 0.6 (pad_2), **solref "0.004 1"**, **solimp "0.95 0.99 0.001"**, no condim given, so **condim 3** (default) |
| Cubies (contact partner) | `M1Params.cubie_*` | condim 3, μ 0.2, solref (0.001, 1), solimp (0.95, 0.99, 0.0005), mass 3.4 g, ball/hinge joint on the core, armature 1e-6 |
| Global options (copied from the cube) | `M1Params` + `integration_hold_m2.py` l. 93 | dt 0.5 ms, implicitfast, elliptic, impratio 10, Newton, 100 iterations, **tolerance 1e-10** |

Contact mixing rule (`FACT`, `modeling.rst` §"Contact parameters"/solmixing; https://mujoco.readthedocs.io/en/stable/modeling.html#contact-parameters): when one geom has higher `priority`, its condim, friction, solref and solimp are used. **The pad-cubie contacts therefore use the Menagerie pad values: time constant 4 ms, solimp 0.95/0.99/1 mm, condim 3.** The README's own text agrees ("G2 pads (condim 3, μ 0.7/0.6)").

`INFERENCE`: the friction time constant of 4 ms is 4× the smallest value that refsafe allows at dt 0.5 ms (1 ms; see §2). By the formula in §1, this alone makes the creep about 4× faster than it needs to be.

---

## 1. Mechanism: why a grip far inside the cone still creeps

**FACT (docs).** "Even when the tangential force required for static equilibrium lies strictly inside the contact friction cone, MuJoCo's regularized soft-contact model does not guarantee an exact zero-velocity stick state. In the recommended elliptic contact model, friction dimensions have no position residual and are purely damped, so a persistent tangential load can produce a nonzero steady slip velocity. This is expected behavior."
Sources: local `…/mujoco/doc/modeling.rst` l. 1733–1740 ("Slow slippage"); online https://mujoco.readthedocs.io/en/stable/modeling.html#preventing-slip (same text, checked 2026-11-13). Further sources:
- `overview.rst` l. 863–881 ("Softness and slip"): "gradual contact slip cannot be avoided… it is not trying to prevent slip in the first place".
- `computation/index.rst` l. 1278–1283: friction rows have z = 0, ω ≠ 0.
- A maintainer called this "WAI" (working as intended): https://github.com/google-deepmind/mujoco/issues/3328 (first comment, yuvaltassa, 2026-06-17).

**FACT (docs and source): the per-row model.**
- The reference acceleration is a_ref = −B·(Jv) − K·I·r. For friction rows of elliptic cones r ≡ 0 and K = 0, so a_ref = −B·v_t (`computation/index.rst` l. 1650–1660).
- The damping is B = 2/(solimp[1]·τ) in the standard format, and B = −solref[1]/solimp[1] in the direct format (`engine_core_constraint.c` @4.0.1, `mj_makeImpedance`).
- The regularizer is R = (1−imp)/imp · Â, where Â is a body-based approximation of the diagonal of the constraint-space inverse inertia. Â is computed from `body_invweight0` at `qpos0` (`computation/index.rst` l. 1600–1630; source `dA[i+j] = tran` for the tangential rows).
- **Friction rows are re-assigned R_t = R_n / impratio** after the per-row loop. For condim > 3, further rows get R_j = R_t·μ₁²/μ_j² (source lines `R[i+1] = R[i]/impratio`, `R[i+j+1] = R[i+1]*friction[0]^2/friction[j]^2`).
- The force relation is R·f = a_ref − a_c (`computation/index.rst` §Adhesion, which derives this identity).

**INFERENCE: steady creep.** At constant slip, a_c ≈ 0, so −B·v_t = R_t·f_t, which gives

  v_creep ≈ R_t·f_t / B_t = [(1−imp)/imp] · Â_t · f_t · solimp[1] · τ_f / (2·impratio)

This holds per contact. Contacts in parallel share the load, so more contact points give a smaller f_t per contact and a slower creep.

Consequences, each checkable:
1. **The rate does not depend on the normal force.** Only f_t, the share of the weight each contact carries, enters. This matches the measured 0.02 mm/s at 10, 30 and 50 N. It is a good sign that the mechanism is right.
2. **The rate is proportional to 1/impratio, to τ_f, and to (1−imp)/imp.**
3. **refsafe sets a floor of τ_f ≥ 2·dt**, so the best case scales with the timestep: v_min ≈ R_t·f_t·solimp[1]·dt. (`engine_core_constraint.c` applies `max(solreffriction[0], 2*timestep)` as well as `max(solref[0], 2*timestep)`. Docs: `XMLreference.rst` l. 636–644.)
4. `INFERENCE`: Â for a pad-cubie contact comes from the cubie body's `body_invweight0`. That value is computed from the joint-space mass matrix, which does not include the M2 welds (they are equality constraints). The regularizer therefore sees a 3.4 g cubie on a ball joint with armature 1e-6, not the 90 g welded cube. Â is large, so R and the creep are larger than for an equivalent single rigid cube. Rough order of magnitude (`ASSUMPTION`: Â ≈ 100 kg⁻¹, f_t ≈ 0.03 N per contact, imp 0.95, τ 4 ms, impratio 10) gives ≈ 0.03 mm/s. That is the same order as the measurement, but **unverified**: the real `efc_R`, `efc_KBIP` and `body_invweight0` must be logged (§6, run B0).

**Doc and code disagree (FACT, both read; not tested).**
- The Friction section of `modeling.rst` (l. 404–421) says friction rows always use d₀ = solimp[0], because d(r) is evaluated at r = 0.
- In the 4.0.1 source, for an *elliptic contact* `getimpedance` is evaluated **at the contact's normal penetration**. The resulting imp sets R for all rows, and the friction R is then R_n/impratio. So the friction impedance follows the penetration through the solimp sigmoid. The statement in the docs does hold for joint/tendon friction-loss rows.
- For the G2 pads (width 1 mm, midpoint 0.5, power 2) at 0.07–0.29 mm penetration, imp ≈ 0.950–0.957 (`INFERENCE`, hand calculation). The effect is under 15 %. **A flat solimp (solimp[0] = solimp[1]) removes the ambiguity** (`getimpedance` returns a constant).

---

## 2. Options: mechanism, expected effect, side effects

Expected-effect factors are `INFERENCE` from the formula in §1, relative to the current state (τ_f 4 ms, imp ≈ 0.95, impratio 10, dt 0.5 ms, about 0.02 mm/s), unless an empirical source is named.

### 2.1 `impratio` (global, `<option impratio>`)
- **Mechanism (FACT):** sets R_t = R_n/impratio, so friction rows are "harder" than normal rows. It only applies with elliptic cones. Docs: `XMLreference.rst` l. 367–375; `modeling.rst` l. 1744–1747 and 1979–1984. The docs suggest 10 for manipulation and 10–100 for legged locomotion, and say: "reduces slow slippage… without… guaranteeing exact sticking".
- **Expected effect:** v ∝ 1/impratio. 10 → 100 gives about 10× slower creep (≈ 0.002 mm/s). Empirical (`FACT`, third-party data, MuJoCo 3.8.1 / 3.12.1, a different model): impratio 1/10/100 gave 1552/155/15.3 µm/s (#3328; reproduced in PR #3526).
- **Side effects:**
  - It is **global**. It also changes every cubie-cubie elliptic contact, i.e. the Phase-1 turning mechanics that the scored E1/E2 runs used with impratio 10. A change breaks comparability with those runs and needs its own preregistration and DECISION_LOG entry.
  - Conditioning: issue #3628 (open) shows Newton ending at a non-converged qacc **only with elliptic cones + high impratio + a tight `ls_iterations`** (≤ 22). Keep `ls_iterations` at its default of 50 and monitor the solver gradient.
  - Cost per step: about zero.
  - Energy: friction rows are pure damping, so stiffer damping does not add energy (`INFERENCE`).
  - **Not for pyramidal cones** (docs).

### 2.2 Friction time constant: pad `solref`, or `solreffriction` on explicit `<pair>`
- **Mechanism (FACT):**
  - For elliptic friction rows only the time constant (standard format) or the damping (direct format) matters (`modeling.rst` l. 404–421).
  - **`solreffriction` exists only on `contact/pair`** (and on joint/tendon friction loss). It does **not** exist on `geom` (`XMLreference.rst` l. 4328–4340). It works only with elliptic cones, and the default "0 0" means "same as solref".
  - An explicit `<pair>` replaces **all** contact properties with its own values or defaults (pair friction default "1 1 0.005 0.0001 0.0001"). So friction, condim, solref and solimp must be restated.
  - Source (`engine_collision_driver.c` @4.0.1, `filterCollisionPair`): a dynamic contact for a geom pair that also has an explicit `<pair>` is **skipped**, so no duplicate contacts appear.
- **Two ways to apply it:**
  - (a) Change the pad class `solref` 0.004 → 0.001. This is simplest, and because pad priority is 1 it reaches only pad contacts. It also stiffens the **normal** direction.
  - (b) Add `<pair geom1=pad geom2=cubie solreffriction="0.001 1" …>` for the 4 pads × 26 cubie geoms. Only the friction rows change.
- **Expected effect:** v ∝ τ_f. 4 ms → 1 ms (the refsafe floor at dt 0.5 ms) gives about **4×** (≈ 0.005 mm/s). In #3328 (`FACT`, third-party), solref 0.02 → 0.002 at dt 2 ms gave only about 3× (155 → 51 µm/s). `INFERENCE`: refsafe clamps 0.002 to 2·dt = 0.004 there, so the effective change was 5×, and that run also changed the normal force (12 → 60 N).
- **Direct format (negative solreffriction)** escapes refsafe, but by our analysis of the update (v⁺ ≈ v(1 − h·imp·B)) the refsafe floor is already about deadbeat (h·imp·B ≈ imp/solimp[1] ≈ 1). Damping beyond about 2/h oscillates. Gain ≤ ~1.5–2× with a stability risk (`INFERENCE`, not tested).
- **Side effects:**
  - (a) Stiffer normal contact. Rest penetration scales with (1−d)·τ² (doc formula, `modeling.rst` §solref), so it would fall about 16× (from 0.07–0.29 mm). Harder impacts at grasp closure: the earlier failed step-close attempt shows this matters. The G2 force calibration (T4, box) should be re-checked.
  - (b) More MJCF (~104 pairs). Local, and leaves the cube mechanics untouched.
  - Both: no extra cost per step beyond possibly more Newton iterations.

### 2.3 `solimp` impedance (pad geoms; d₀ = solimp[0])
- **Mechanism (FACT):** R = (1−imp)/imp·Â. The docs say "rest penetration and static-friction creep both scale with 1 − d₀… raising d₀ from 0.9 to 0.95 halves both, but costs solver iterations… Lowering solref and switching to elliptic cones are much stronger levers, so try those first" (`modeling.rst` l. 2014–2023). The upper limit is imp ≤ 0.9999 (`mjMAXIMP`, `mjmodel.h` @4.0.1). Contacts have **no `solimpfriction`**, so solimp always changes normal and friction together.
- **Expected effect:** with a flat solimp, (1−d)/d goes from 0.0526 (d 0.95) to 0.0101 (0.99, **≈ 5×**) or 0.0010 (0.999, ≈ 50×).
- **Side effects:**
  - Harder normal constraint: penetration ↓, impact forces ↑.
  - The overview (l. 868–873) warns that such changes "often require smaller time steps to keep the simulation stable".
  - Possibly more solver iterations.
  - If set on the pads (priority 1), only pad contacts change.

### 2.4 NoSlip post-processing (global, `noslip_iterations`, `noslip_tolerance`)
- **Mechanism (FACT):**
  - After the main solver, NoSlip runs a PGS sweep over the friction rows with R = 0 (hard). It projects onto the true Coulomb cone (`solveQCQP` with `con->friction`).
  - **It also re-solves all dof/tendon friction-loss rows** (the "dry friction" sweep in `engine_solver.c` @4.0.1, `solNoSlip`).
  - `noslip_tolerance` (default 1e-6) is only an early-stop threshold on cost improvement. It does not bound the residual slip.
  - Docs: `computation/index.rst` l. 1526–1533; `modeling.rst` l. 575–586, 1748–1755 and 1984–1986; `XMLreference.rst` l. 495–506; `overview.rst` l. 875–880.
- **Expected effect:** the strongest lever. The docs say 1–3 iterations "usually sufficient" and suppress drift strongly, "Exact zero slip is not guaranteed". `FACT`, third-party: 10 iterations cut creep about 110× (155 → 1.41 µm/s; #3328, reproduced in PR #3526).
- **Side effects (FACT, docs unless noted):**
  - About 2× step time.
  - Pays the PGS setup cost even under Newton. `INFERENCE`: likely more than 2× here, because the M2 model has 149 equalities (~900 weld rows); measure it.
  - "No longer solving a well-defined optimization problem… ad hoc".
  - Inverse dynamics becomes ill-defined.
  - "Occasional chatter in overconstrained grasps". Our grasp *is* overconstrained: two flat pads on 6 welded cubies each.
  - "Some instabilities in models with more complex interactions among multiple contacts".
  - Issue #2423 (open; reproduced on 3.17.0/4.0.0 wheels): **NoSlip + joint `frictionloss` + `damping` under an implicit integrator gives unphysically slow decay** (about 17 000 vs 67 steps to stop). The cubie joints (frictionloss 0.0005, damping 0.0005) and the arm joints (frictionloss 1) all have that combination under `implicitfast`. **NoSlip would therefore alter the cube's turning resistance**, which is project-critical.
  - Not supported in MJX/Warp (`mjx.rst` l. 505).
  - Global: breaks comparability with the scored runs.

### 2.5 Smaller timestep
- **Mechanism:** refsafe floor τ ≥ 2·dt (FACT). B can grow only if dt shrinks.
- **Expected effect:** with τ_f kept at 2·dt, v ∝ dt (`INFERENCE`). 0.5 → 0.25 ms gives 2× **only if the pad τ is also lowered**. With the pad τ left at 4 ms, a smaller dt changes almost nothing (`INFERENCE`).
- **Side effects:** about 2× wall time per halving (the integration test already runs at only 0.2–0.4× real time). Breaks timestep parity with the scored cube runs.

### 2.6 condim 4 or 6
- **Mechanism (FACT):** condim 4 adds torsional friction (resists rotation about the normal), condim 6 adds rolling. Docs list this under "torsional friction is insufficient" (`modeling.rst` l. 1700–1711), not under slow slippage. The extra rows get R_j = R_t·μ₁²/μ_j² (source). With μ_torsion = 0.005 and μ₁ = 0.7, R_j ≈ 2·10⁴·R_t, so these rows are very soft.
- **Expected effect on translational creep: none.** `FACT`, third-party: condim 6 changed 310 → 307 µm per 2 s (#3328; PR #3526). It might reduce the rotation creep about the pad normal (already 0.001–0.007° per 3 s). Multi-point pad contacts already resist that rotation through tangential couples (`INFERENCE`).
- **Side effects:** more constraint rows. With condim 3 pads and priority 1, the cubie condim is ignored, so this has to be set on the pads.

### 2.7 Pyramidal vs elliptic cones (global)
- **Mechanism (FACT):** the pyramid's edges carry a shared position residual, so the tangential difference is still purely velocity-damped (`INFERENCE`). Pyramidal sets R_py = 2·μ_reg²·R_n (source). `solreffriction` is ignored. "Avoid large impratio with pyramidal cones" (docs). The soft-contact dynamics differ from elliptic even in the limit (`computation/index.rst` l. 1704–1740). The docs recommend elliptic + large impratio + Newton for slip (`modeling.rst` l. 551–556).
- **Expected effect: worse or no better.** `FACT`, third-party: pyramidal at impratio 1 gave 2301 µm/s vs elliptic at impratio 1 1552 (#3328). A maintainer suggested elliptic for anisotropic slip (#2638).
- **Side effects:** global; changes the cube's contact dynamics. **Not recommended.**

### 2.8 Other documented or available levers
- **Newton tolerance:** already 1e-10. This is the docs' "very small tolerance" recommendation (`modeling.rst` l. 555–562). No gain expected. Do not lower `ls_iterations` (#3628).
- **More contact points:** v ∝ load per contact (`INFERENCE`). The Menagerie advice is pad boxes and "more contact points" (`modeling.rst` l. 1713–1721; #786, kevinzakka). This is relevant to the custom fingertip design (D-04) and costs nothing in solver settings. `multiccd`/`nativeccd` are on by default.
- **`diagexact` flag:** computes the exact Â at runtime instead of at `qpos0`. It changes R by the ratio of exact to approximate Â, in either direction. It does not fix creep, but it is useful as a diagnostic (`XMLreference.rst` l. 745–757). It still ignores the welds, since it uses M only (`INFERENCE`).
- **`discrete` integrator (new Sept 2026, "under active development"):** refsafe is not applied, and rows are implicit. By reading the 4.0.1 code, elliptic friction R is still R_n/impratio, while a_ref is divided by (1 + h·B), so v ≈ R_t·f_t·(1/B + h). The floor is still ∝ h (`INFERENCE`, untested). **Not recommended now.**
- **"Stiction" (position-referenced static friction):** PR #3349 (kevinzakka, 2026-06-17) was **closed without merging**. No `stiction` flag exists in the 4.0.1 docs (grep). **Not available.**
- **Controller compensation** (feedback re-grasp or position hold on cube pose): does not remove creep, only masks it. It is a valid controller-level mitigation but must not use privileged state at evaluation (CLAUDE.md).
- **Contact override (`o_solref`/`o_solimp`, `override` flag):** global and only for interactive sweeps (`modeling.rst` l. 2000–2003). It would also hit the cubie-cubie contacts. Use it for diagnosis only.

---

## 3. Ranking (recommendation, `PROPOSAL`)

| Rank | Option | Expected creep | Locality | Main cost or risk |
|---|---|---|---|---|
| **1** | **Stiffen the pad contacts only**: pad `solref` τ 4 → 1 ms (= 2·dt) **plus** flat pad `solimp` d₀ 0.95 → 0.99. Or, to leave the normal direction untouched, use `<pair … solreffriction="0.001 1">` | ≈ 4× × 5× ≈ **20× lower** (~0.001 mm/s) (`INFERENCE`) | Pad contacts only (priority 1 / pair); cube mechanics unchanged | Stiffer normal impacts and smaller penetration. Re-check grip calibration (T4) and grasp closure. MJCF change is local to `build_model.py` |
| **2** | **impratio 10 → 30–100** | 3–10× lower (consistent with #3328 data) | Global: changes cubie-cubie contacts too | Breaks parity with the scored E1/E2 settings. Newton line-search sensitivity (#3628). Needs preregistration |
| **3** | **NoSlip, 1–3 iterations** | Strongest (~100× in #3328) but not exactly zero | Global, and also re-solves joint friction-loss rows | ~2×+ step time. Ad hoc. Chatter in overconstrained grasps. Corrupts frictionloss + damping dynamics (#2423), i.e. cube turning resistance. Inverse dynamics ill-defined |

Not recommended: pyramidal cones (worse), condim 4/6 for this purpose (no effect on translational creep), the discrete integrator (experimental), "stiction" (not merged). A smaller timestep helps only together with option 1 and costs linear wall time.

Expected floor for option 1 plus impratio 100, if ever needed: about 10⁻⁴ mm/s (≈ 0.4 mm/hour), still not zero (`INFERENCE`). Exact zero is impossible with any documented setting (FACT, docs).

---

## 4. What a physics reviewer should know (project constraints)

- All options are **contact-model parameters**. None edits state or injects a turn, so they are compatible with the "forces only" rule. NoSlip replaces soft friction forces with hard-Coulomb ones computed after the main solve. It is still a force model, but an ad hoc one (docs). If adopted, it must be used identically in training and evaluation and recorded in the DECISION_LOG.
- Global options (impratio, cone, NoSlip, timestep) change the cube's validated mechanics. Pad-local options do not. That is why option 1 is ranked first, even though NoSlip is the strongest.
- Real pads also creep (viscoelasticity), but by a different mechanism. Matching the MuJoCo creep to reality would need measured hold data (`ASSUMPTION`: no such data exist in the project yet).

---

## 5. Open questions (unverified)

1. The actual Â, R_t and B for the pad-cubie rows: compute from `m.body_invweight0`, `d.efc_R`, `d.efc_KBIP` at the hold state.
2. Does v ≈ Σ-weighted R_t·f_t/B predict the measured 0.02 mm/s to within 2×? If not, part of the creep has another source, e.g. weld-row compliance or the gripper linkage.
3. The doc-vs-code impedance discrepancy in §1. It could be reported upstream later; nothing has been filed.
4. NoSlip cost on this ~900-row model.

---

## 6. Minimal test plan (`PROPOSAL`; unscored; run **after** the scored run finishes)

**Scene:** `integration_hold_m2.py`, unchanged procedure (2 s gravity-off ramped close, then the hold), 30 N grip, extended hold **10 s**. Spot-check 10 and 50 N for the best variant only. Single thread; MuJoCo 4.0.1; deterministic (log the config hash, hardware and wall time).

**Primary metric:** creep rate = least-squares slope of core slip relative to the gripper over t = 2–10 s (mm/s). Also report the end slip and the rotation rate.
**Secondary metrics:**
- max pad penetration;
- pad normal and tangential force (mean and std over the last 1 s; the std is the chatter indicator);
- Newton `solver_niter` and final gradient (max over the run);
- steps/s;
- cube kinetic energy over the hold (must not grow);
- for NoSlip, the `fwdinv` flag discrepancy.

**Diagnostic logged in B0:** per pad-cubie contact, `efc_R`, `efc_KBIP[B]`, f_t and `body_invweight0`. From these compute v_pred = R_t·f_t/B and compare with the measured rate. This is the falsification test of §1.

| Run | Change from baseline | Prediction (`INFERENCE`) |
|---|---|---|
| B0 | none (repeat; check determinism vs README) | ≈ 0.02 mm/s; v_pred within 2× |
| A1 | pad solref 0.004 → 0.001 | ≈ 4× lower |
| A2 | pad solimp → flat 0.99 0.99 0.001 | ≈ 5× lower |
| A3 | A1 + A2 | ≈ 20× lower; penetration ≲ 0.01 mm |
| A4 | explicit `<pair>` pad×cubie, pad values restated, `solreffriction="0.001 1"` only | ≈ 4× lower; normal force and penetration ≈ B0 |
| B1 / B2 | impratio 30 / 100 | 3× / 10× lower |
| C1 / C2 | noslip_iterations 1 / 3 | ≫ 10× lower; ≥ 2× slower |
| D1 | A3 + dt 0.25 ms + pad τ 0.0005 | ≈ 2× lower than A3; 2× wall time |
| E1 | pad condim 4 (control) | translational creep ≈ B0 |

Budget: about 11 runs × 24 000 steps at ~500–800 steps/s, roughly 6–10 min single-thread in total.
**Global-option guard:** if B or C variants are pursued, rerun one short M2 turn smoke case (`experiments/M2_switched_welds/run_m2.py`, unscored) with the same option, and compare turn resistance and settling against the scored settings, before any adoption.
**Acceptance target (`PROPOSAL`, user to set):** creep ≤ 0.001 mm/s (≤ 0.06 mm/min) at 10–50 N, no growth in cube KE, no new non-pad contacts, penetration > 0, Newton gradient ≤ 1e-6, throughput loss ≤ 25 %.
**Negative results are kept.** If v_pred disagrees with the measurement by more than 2×, stop tuning and investigate the other compliance sources first.

---

## 7. Sources (all accessed 2026-11-13)

Local MuJoCo 4.0.1 docs (WSL `~/.venvs/rubiknetic/lib/python3.12/site-packages/mujoco/doc/`):
- `modeling.rst`: solver settings l. 530–591; Friction l. 404–421; solref/solimp l. 290–402; mixing l. 469–480; Preventing slip / Slow slippage l. 1686–1755; tuning l. 1979–1986, 2010–2023.
- `overview.rst` l. 850–881.
- `XMLreference.rst`: impratio l. 367–375; cone l. 444–448; noslip l. 495–506; refsafe l. 636–644; diagexact l. 745–757; pair/solreffriction l. 4275–4340.
- `computation/index.rst`: augmented dynamics l. 1270–1300; NoSlip l. 1526–1533; Parameters l. 1578–1700; Friction cones l. 1704–1740; discrete-integrator limits l. 695–745.

Online docs (text matches the local copy for the slip sections, checked by fetch):
- https://mujoco.readthedocs.io/en/stable/modeling.html#preventing-slip
- https://mujoco.readthedocs.io/en/stable/modeling.html#friction
- https://mujoco.readthedocs.io/en/stable/XMLreference.html#option
- https://mujoco.readthedocs.io/en/stable/computation/index.html

Source code, tag 4.0.1 (Apache-2.0):
- https://github.com/google-deepmind/mujoco/blob/4.0.1/src/engine/engine_core_constraint.c: `getsolparam` refsafe, `getimpedance`, `mj_makeImpedance` (impratio, friction R), contact `diagApprox`, `mj_referenceConstraint`.
- https://github.com/google-deepmind/mujoco/blob/4.0.1/src/engine/engine_solver.c: `solNoSlip`, l. 778–975.
- https://github.com/google-deepmind/mujoco/blob/4.0.1/src/engine/engine_collision_driver.c: `filterCollisionPair`, l. 682–692 (explicit pair suppresses the dynamic duplicate).
- https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjmodel.h: `mjMAXIMP` 0.9999.

GitHub issues and PRs (read-only via `gh api`; third-party measurements, not reproduced by us):
- https://github.com/google-deepmind/mujoco/issues/3328: creep characterization; maintainer reply "WAI".
- https://github.com/google-deepmind/mujoco/pull/3526: docs PR, merged 2026-09-08, which re-measured the #3328 cases on main.
- https://github.com/google-deepmind/mujoco/pull/3349: "Static friction for elliptic contacts", closed unmerged.
- https://github.com/google-deepmind/mujoco/issues/2423: NoSlip × frictionloss × damping.
- https://github.com/google-deepmind/mujoco/issues/3628: Newton line search with elliptic + impratio 10.
- https://github.com/google-deepmind/mujoco/issues/786: grasp; Menagerie pad boxes; high impratio needs elliptic.
- https://github.com/google-deepmind/mujoco/issues/565: maintainer suggests NoSlip; notes it is slow, PGS-based.
- https://github.com/google-deepmind/mujoco/issues/2638: maintainer suggests elliptic over pyramidal.

Project files read: `experiments/P2_robot_model/README.md`, `integration_hold_m2.py`, `src/rubiknetic/cube_physics/m1_model.py`, `experiments/M2_switched_welds/m2_model.py`, `third_party_cad/robot/generated/xarm7_g2_1305+.xml`.
