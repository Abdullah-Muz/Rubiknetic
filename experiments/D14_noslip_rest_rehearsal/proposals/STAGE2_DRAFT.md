# DRAFT — not approved

# D14 Stage 2 — the rest of the Part G probe at `noslip_iterations` 10 (protocol draft)

**Status:** draft written by a drafting subagent on 2026-11-23, for the main session to verify and for the user to
approve. It is not in force, and nothing here has been run. P-73 (`docs/DECISION_LOG.md`) approved the staged plan.
Stage 2 runs only on the user's go after the Stage 1 report (`experiments/D14_noslip_rest_rehearsal/PROTOCOL.md`).

**Scope:**
- UNSCORED and reported only. M5 stays NOT PASSED, and Part G's outcome stays as reported (no arm selected).
- Stage 2 changes one simulation setting, `noslip_iterations` from 0 to 10, in every trial model it compiles. That
  setting was chosen after M5, Part G and D13 failed or reported, and this is disclosed. Nothing here adopts it for G1.
- Stage 2 writes only under `experiments/D14_noslip_rest_rehearsal/`. It edits nothing under `src/`, the scored
  runners, ER7, ER9, D13 or Stage 1's code.
- Seeds come only from the committed Part G probe and ER7 trial lists (rehearsal range 16000–16999; listed in §1).
  Seeds 17000–17999 and 10000–10999 stay untouched. Stage 2 also leaves D12's reserved block 16900–16999 and the
  deferred U5 block 16700–16739 unused.

**Labels:**
- `FACT`: read from a file and line given here, or computed from committed records by a read-only script.
- `INFERENCE`: reasoning, not tested.
- `PROPOSAL`: a design choice for the user.
- `OPEN`: a decision this draft does not make.
- `UNVERIFIED`: a claim not checked in this session.

---

## 1. Scope and exact trial list

### 1.1 Which probe trials (`FACT`)
- The Part G probe ran four sub-experiments per arm. `PROBE_EXPS = ("E1-1", "E1-2", "E1-5", "E1-5s")` and
  `PROBE_COUNTS = {"E1-1": 20, "E1-2": 24, "E1-5": 42, "E1-5s": 20}` are at
  `experiments/ER9_anchored_core_layouts/er9g_run.py` l.94–95.
- `probe_base()` (l.462–466) filters ER7's 204-job list (`er7_run.er7_jobs()`, `er7_run.py` l.128–138) to those
  experiments and asserts the counts.
- Every job is then wrapped by `make_job()` (l.456–459) and run by `run_one()` (l.500–541) in a fresh fork worker.

**Stage 2 runs E1-2, E1-5 and E1-5s.** Their trial IDs and seeds are exactly the committed ones. They were read from
the committed records (`results/hybrid_g/probe/<arm>/<exp>/*.json.gz`; ER7 `results/L0/<exp>/`), and they are
identical in PG8, PG20 and ER7 L0.

| Exp | Kind (`M4.run_trial`) | Trials per arm | Seeds | Trial IDs | What varies |
|---|---|---|---|---|---|
| E1-2 | `seq`, one quarter turn | 24 | 16100–16123 (24 seeds) | `U_s16100`, `U_s16101`, `Up_s16102`, `Up_s16103`, `R_s16104` … `Bp_s16123` | 6 faces (U R F D L B) × (2 × q1, 2 × q3) |
| E1-5 | `forgive` | 42 | 16500–16541 (42 seeds) | `forgive_<±deg>_s<seed>` | commanded U misalignment −20° … +20° in 1° steps, with 0° twice (`forgive_+0_s16500`, `forgive_+0_s16521`) |
| E1-5s | `snap` | 20 (12 scored) | 16551, 16552, 16553, 16555, 16558, 16561, 16562, 16563, 16565, 16568 | `snap_<±δ>_s<seed>` | δ = ±1, ±2, ±3, ±5, ±8°, two repetitions. Scored when \|δ\| ≥ 3° (`snap_is_criterion`, `E4_scored_m4/run.py` l.498): 12 of 20 |

That is **86 trials per arm**.

### 1.2 E1-1 is not rerun in Stage 2 (`PROPOSAL`)
- Stage 1 (D14) already runs the E1-1 rest on seeds 16000–16019 at `noslip_iterations` 10. It uses D13's V2 path: a
  10 s warm-up at frozen settings, then the instrumented 60 s rest with NoSlip (D14 PROTOCOL §3).
- D14's 0–10 s rest rotation is defined as the E1-1 metric (D14 PROTOCOL §5).
- D14 also evaluates G.4 validity on the 60 s rest's class stats for PG8 and PG20 (D14 PROTOCOL §5).
- So Stage 2 **reads** E1-1 from the D14 records, for signal 2 and for E1-1's share of signal 4. It does not rerun it.
- Difference from the probe, disclosed: in the probe's E1-1, both the 10 s scored rest and the 60 s rest ran at the
  same setting (`er7_run.py` l.150 and l.159–166). In D14 the 10 s scored-format trial is a frozen-setting warm-up,
  and the noslip E1-1 metric is the first 10 s of the 60 s rest. ER7's S4 showed that the two metrics are equal at
  frozen settings (`er7_run.py` l.166). Whether they are equal at noslip is not tested (`INFERENCE`: same trial,
  same seed and setup draw, so they should be).

### 1.3 Arms (`PROPOSAL`; see OPEN-1)
- **Eligibility:** an arm enters Stage 2 only if it met D14's Stage 1 signal (P-73: "for arms that pass").
- **PG8 and PG20:**
  - path: `er9g_run.run_one` unchanged, with `install_er7(arm, "N52")` and the class-stats system;
  - D_val 12.0° (`results/hybrid_g/probe/<arm>/environment.json`, `D_val_deg`);
  - `er7_arm` "L0" (`er9g_run.py` l.209–212).
- **L0 (reference arm):**
  - path: ER7's own path (`er7_run.run_one`, er7_arm "L0"), as in D14 (D14 PROTOCOL §3) and as the committed ER7 L0
    records were made;
  - validity reported with M4's legacy magnet statistics only, as in Part G and D14.
- **Maximum size:** 3 arms × 86 = **258 trials**, plus the gate trials of §3.4 (9 if all three arms run).

---

## 2. Signals and the paired comparison

### 2.1 Part G probe signals, quoted (`FACT`, `experiments/ER9_anchored_core_layouts/PROTOCOL.md` §G.8, "Probe signals (fixed now; ER7's criteria)")
> 1. E1-5s: every scored trial passes (|error| ≤ 0.5° after 1 s, from release offsets of 3° or more).
> 2. E1-1: every rest rotation ≤ 0.5° **and** 0/20 D11 slip events over 60 s.
> 3. E1-2 and E1-5: every trial passes.
> 4. No operational trial out of regime under G.4's per-trial rule, with the D_val in force. All probe trials are
>    operational.

**How "passes" and "out of regime" are computed** (`FACT`, code):
- **Part G verdict:** `er9g_run.verdict()` (l.418–433), applied by `apply_verdict()` (l.436–452) and recomputed by
  `pass_g()` (l.780–783). It is M4's criteria with ER7/M4's legacy aggregate-tilt rule 2 removed and replaced by
  G.4's per-class rule (PROTOCOL §G.4, "Per-trial rule").
- **Out of regime:** `oor_reasons()` (l.399–408), cross-checked against `er9g_stats.out_of_regime`:
  - CE tilt > 5°, CE clamped z, CE perpendicular;
  - PCon tilt > 20°, PCon perpendicular;
  - PCoff tilt > 7.5°, PCoff clamped z, PCoff perpendicular;
  - PP3 tilt > 7.5°, PP3 clamped z, PP3 perpendicular;
  - `cross_near` > 0.
- **E1-5s pass** (`E4_scored_m4/run.py` l.468–471 and l.496–502): integrity, not aborted, `t0_solved`, final state
  valid and solved, and, for scored trials, |`U_err_after_1s_deg`| ≤ 0.5°.
- **E1-2 pass** (`scored.py` l.297, l.310–312): per move, an oracle-consistent observed move, |turn error| ≤ 2°,
  non-target drift ≤ 1°, penetration ≤ 0.5 mm, no radial pop above 0.3 mm, and causality. Also integrity, not aborted
  and the final state matching the oracle (thresholds at `scored.py` l.33–45).
- **E1-5 pass** (`scored.py` l.392–397): categorical. Completed, no net move, or UNKNOWN is allowed; an illegal or
  oracle-mismatched transition fails. Also integrity, not aborted, and `t0_solved`.
- **Signal evaluation:** `probe_signals()` (l.791–809).

**Stage 2 applies these signals unchanged, at noslip** (`PROPOSAL`). Per eligible arm:

| Signal | Source at noslip | Evaluated by |
|---|---|---|
| 1 snap-back | Stage 2 E1-5s (12 scored of 20) | `pass_g` on records with `snap_is_criterion` |
| 2 rest | **D14 (Stage 1)**: its signal per arm (0–10 s rest ≤ 0.5° on all 20 seeds, and no D11 event over 60 s) | read from D14's report; not rerun |
| 3 E1-2 and E1-5 | Stage 2 E1-2 (24) and E1-5 (42) | `pass_g` |
| 4 validity | Stage 2's 86 trials (G.4 rule at D_val 12.0°), **plus** D14's 20 rests (D14's validity measure) | `oor_g` / `verdict` |

- For L0: Part G's signals were written for the Part G arms. L0 is reported against the same items, with validity
  read from M4's legacy statistics (max near tilt ≤ M5's 5°), as Part G and D14 do. **No new threshold is introduced.**
- **Rule for failures (`FACT`, PROTOCOL §G.4, "Rules by experiment"):** a trial that aborts (`NumericalFailure`,
  `EditAuditError`) or raises a harness exception fails. It is not excluded and not rerun. This applies unchanged to
  any NoSlip instability.

### 2.2 Paired comparison against the committed frozen-setting records (`PROPOSAL`; reported, not a signal)
- **Pairs:** every Stage 2 record is paired by (arm, exp, trial ID) with the committed frozen-setting record:
  - PG8 and PG20: `experiments/ER9_anchored_core_layouts/results/hybrid_g/probe/<arm>/<exp>/<tid>.json.gz`, commit
    `20cdcfe` in their `environment.json`;
  - L0: `experiments/ER7_core_magnet_rehearsal/results/L0/<exp>/<tid>.json.gz`.
- **Per pair:**
  - the pass flag, frozen against noslip; every flipped flag, with its `fail_reasons`;
  - E1-2: `turn_error_deg`, `nontarget_drift_deg`, `max_turner_torque_Nm`, `penetration_mm`, causal fields, and the
    D8-0 misalignment after the move;
  - E1-5: `outcome` (completed / no_net_move / blocked_unknown / illegal_transition), `U_misalignment_deg`,
    `R_rotation_deg`, `U_change_during_R_deg`;
  - E1-5s: `U_err_after_release_deg`, `U_err_after_1s_deg`, `misalignment_end`;
  - per-class stats (G.4 fields), the largest path deviation d, and the legacy 20° proxy flag;
  - `aborted` and `numerical_failures`;
  - wall time ratio (noslip `er7_wall_s` / frozen `er7_wall_s`).
- **Turner torque:** reported as in G.8, "Reported (pre-declared, not signals)":
  - per arm: median, p99 and max per move;
  - moves above 0.45 N·m, above 0.5 N·m, and at the clip (≥ 0.999 N·m, `CLIP_NM`, `er9g_run.py` l.109);
  - frozen against noslip, beside the realism reference (about 0.2 N·m) and the warning level (about 0.45–0.5 N·m)
    of G.1. These are reported, not limits.
- **Paired direction counts:** for E1-2 per-move peak torque and E1-5s |error after 1 s|, the number of trials in
  which noslip is higher or lower, with `er9g_run.sign_test()` (l.693). Reported only, with no pre-set reading
  (OPEN-7).
- **Frozen baseline for the reader** (`FACT`, `results/hybrid_g/probe/writeup.md` §(b) and §(c)):

  | Arm | Signals 1 / 3 / 4 at frozen | Snap-back max \|err\|, scored | E1-2 turner median / p99 / max (N·m) | Moves > 0.5 N·m | At clip |
  |---|---|---|---|---|---|
  | PG8 | met / met / met | 0.105° | 0.378 / 0.672 / 0.681 | 4 of 24 | 0 |
  | PG20 | met / met / met | 0.032° | 0.576 / 0.863 / 0.886 | 19 of 24 | 0 |
  | L0 (ER7) | — | 0.118° | 0.144 / 0.460 / 0.461 | 0 of 24 | 0 |

---

## 3. Injection path: where each trial's MuJoCo model is compiled

### 3.1 How D13 and D14 inject NoSlip (`FACT`)
- `d13_run.with_noslip(xml, n)` (`experiments/D13_rest_slip_mechanism/d13_run.py` l.104–107) asserts that the XML has
  exactly one `<option ` element and no `noslip_iterations`. It then inserts `noslip_iterations="n"`.
- `d13_rest` (l.170–176) replaces `scored.build_m1_xml` with a wrapper **only while `scored.Trial(...)` is
  constructed**, then restores it.
- The compiled options, including `noslip_iterations`, are recorded from the trial model (l.180–184).
- `M1Params` has no NoSlip field (`src/rubiknetic/cube_physics/m1_model.py` l.86–95), and the `<option>` element is
  written at l.194–196. So `params_for` overrides cannot set it, and an XML edit is the only route that changes no
  committed file.

### 3.2 Call chain of a Stage 2 trial (`FACT`, read from the code)
**PG8 and PG20 (er9g path):** `er9g_run.run_one` (l.500)
- → `LY.install_er7` (l.509; `er9g_layouts.py` l.214–267)
- → `M4.use_magnets` (l.514), which now resolves to `use_arm` (`er9g_layouts.py` l.232–251)
- → `E7.run_one` (l.517; `er7_run.py` l.142–168)
- → `R.run_job` (`E5_scored_m5/run.py` l.304–321)
- → `M4.run_trial` (`E4_scored_m4/run.py` l.595–636), which calls `use_magnets` again (l.602; cached, no compile)
  and then dispatches on the kind:
  - `seq` → `scored.run_sequence_trial` (l.610)
  - `forgive` → `scored.run_forgiveness_trial` (l.618)
  - `snap` → `d8_1b_stage1.run_snap` (l.626)

**L0 (ER7 path):** the same chain from `E7.run_one`, with `M4.use_magnets` left as M4's original
(`E4_scored_m4/run.py` l.334–353), because `er7_run.setup_arm("L0")` changes nothing (`er7_run.py` l.115–118).

**Module identity.** Every module in the chain imports the scored harness as the package module
`rubiknetic.cube_physics.scored`:
- `E4_scored_m4/run.py` l.50;
- `E5_scored_m5/run.py` l.63;
- `er7_run.py` l.60;
- `d8_1b_stage1.py` l.55 (`as SC`).

So all of them share one module object in `sys.modules`. `INFERENCE` from the imports; Stage 2 should assert
`ST.SC is scored` at worker start.

**Global compile patch.** `M4.configure_process()` (`E4_scored_m4/run.py` l.304–312) replaces
`mujoco.MjModel.from_xml_string` with `_compile_paused` (l.289–301, patch at l.311). `_compile_paused` pauses the
magnet callback, calls the original compiler, and asserts that the magnet body ids match. Every compile below goes
through it.

### 3.3 Every compile site, and whether wrapping `scored.build_m1_xml` reaches it

| # | Site (file:line) | When it runs in Stage 2 | XML source | Reached by a `scored.build_m1_xml` wrapper? | Physics consequence if not reached |
|---|---|---|---|---|---|
| C1 | `src/rubiknetic/cube_physics/scored.py` l.195, `Trial.__init__`: `mujoco.MjModel.from_xml_string(build_m1_xml(params))` | **every trial**, once. E1-2 via `run_sequence_trial` l.243; E1-5 via `run_forgiveness_trial` l.360; E1-1 (Stage 1 only) via `run_rest_trial` l.319 and `d10_rest.instrumented_rest` l.80 | `build_m1_xml`, looked up in `scored`'s module globals at call time (imported at l.28) | **Yes.** Replacing the attribute `scored.build_m1_xml` changes this global. | — (this is the trial model that `mj_step` integrates) |
| C2 | `experiments/D8_alignment/d8_1b_stage1.py` l.142, `run_snap`: `SC.Trial(...)`, i.e. C1 | every E1-5s trial | as C1 | **Yes**, through C1 (`SC` is the same module object) | — |
| C3 | `experiments/ER9_anchored_core_layouts/er9g_layouts.py` l.245, `use_arm`: `M4._compile_paused(build_m1_xml(p))` | PG8 and PG20: once per worker, at `er9g_run.py` l.514, to build the arm's `MagnetSystem` | `build_m1_xml` imported locally from `m1_model` at l.229 | **No** (bound to `m1_model.build_m1_xml`) | **None expected.** The `MagnetSystem` keeps this model only for body ids (`magnets.py` l.523) and the size of `_buf` (`nv`, l.540); `self.m` (l.520) is not read anywhere else in `magnets.py`. The force callback acts on the model MuJoCo passes in, which is the trial model (`apply`, l.686–695; `install`, l.697–698). `noslip_iterations` changes neither body ids nor `nv`, and `_compile_paused` asserts the body ids again on the trial model (`E4` l.299–300). |
| C4 | `experiments/E4_scored_m4/run.py` l.349, `use_magnets`: `_compile_paused(build_m1_xml(p))` | L0 only (ER7 path): once per worker | `build_m1_xml` imported from `m1_model` at module level (l.51) | **No** | None expected, as for C3 (a magnet-system-only model) |
| C5 | `experiments/ER7_core_magnet_rehearsal/er7_run.py` l.108, `use_core` | **not in Stage 2** (C52 arm only) | `m1_model.build_m1_xml` (l.61) | No | n/a |
| C6 | `er7_run.py` l.240, `_s2` | not in Stage 2 (ER7 selfcheck only) | as C5 | No | n/a |
| C7 | `E4_scored_m4/run.py` l.531, `startup_checks` | not in Stage 2: called only from E4's `main` (l.746) and E5's `startup_check` (l.619, `main` l.687), never from `er7_run.run_one` or `er9g_run.run_one` | `m1_model.build_m1_xml` | No | n/a |
| C8 | `d8_1b_stage1.py` l.230, `main` | not in Stage 2: `main()` runs only under `__main__` (l.277–278); E4 only imports the module (l.46) | `m1_model.build_m1_xml` (l.56) | No | n/a |
| C9 | `src/rubiknetic/cube_physics/trials.py` l.54; `scored_m2.py` l.105; `er9g_scan.py` l.122 | not imported by the Stage 2 path | — | n/a | n/a |

- **Snap-back is covered.** E1-5s reaches C1 through `d8_1b_stage1.run_snap` (l.140–142).
- **Forgiveness is covered.** E1-5 reaches C1 at `scored.py` l.360.
- **Turn trials are covered.** E1-2 reaches C1 at `scored.py` l.243.
- **No path is missed that matters.** The two compiles the wrapper does not reach are C3 (PG arms) and C4 (L0). Both
  build the magnet system's bookkeeping model only. `INFERENCE`, from reading `magnets.py`: they carry no dynamics.
- **Grep used** (this session): `from_xml_string|MjModel\.from|build_m1_xml` over `src/` and the modules of the
  chain. No other compile site was found.

### 3.4 Proposed injection, without editing any committed file (`PROPOSAL`)
1. **Where the wrapper is installed.** In the new Stage 2 runner's worker function, before `er9g_run.run_one(job)`
   (PG arms) or `er7_run.run_one(job)` (L0), install it for the whole trial:

   `scored.build_m1_xml = lambda p: D13.with_noslip(orig(p), 10)`

   - Workers are fresh processes that run exactly one trial (`maxtasksperchild=1`, as `er9g_run.run_pool`
     l.871).
   - Each Stage 2 trial constructs exactly one `scored.Trial` (C1).
   - So whole-trial installation is equivalent to D13's construction-only wrapper. NoSlip then covers the trial's
     0.5 s settle and its setup misalignment too, as it does for the D14 rest (`scored.py` l.202–204).
   - It reuses the committed `with_noslip` (`d13_run.py` l.104–107) unchanged, so Stage 1 and Stage 2 edit the XML
     identically.
2. **Do not install it in the parent before the fork.** That way no other process, and no gate trial (item 4),
   inherits it.
3. **Proof per record, read-only:**
   - The wrapper counts its calls. The record stores `noslip_wrapper_calls`; it must be 1, otherwise the run stops
     as a harness error.
   - After the trial, `M4.MagnetMonitor.last.m.opt.noslip_iterations` is read. `MagnetMonitor` replaces
     `scored.Monitor` (`E4` l.312), sets `MagnetMonitor.last = self` (l.368) and keeps the trial model as `self.m`
     (`scored.py` l.122). `run_trial` clears `.last` before each trial (`E4` l.606).
   - The record stores the trial model's `timestep`, `impratio`, `noslip_iterations`, `cone`, `solver`,
     `iterations` and `tolerance`, as D13 does (`d13_run.py` l.180–184).
   - A record whose `noslip_iterations` is not 10 is a harness error: stop and report.
   - Also recorded: `M4._MS.m.opt.noslip_iterations`, which is expected to be 0 (C3 and C4), and `M4._MS.m.nv`,
     which must equal the trial model's `nv`.
4. **Reproduction gate at frozen settings, before any NoSlip trial** (`PROPOSAL`; size is OPEN-2):
   - The same runner, without the wrapper, reruns the first trial of each of E1-2, E1-5 and E1-5s per eligible arm.
   - Each must equal its committed record exactly, ignoring only run metadata and naming fields (`er9g_run.GS_SKIP`,
     l.103–105, for PG arms; `er7_run.SKIP_KEYS`, l.181–183, for L0).
   - Purpose: show that Stage 2's harness reproduces the committed probe, so that any difference after this is the
     setting.
   - D13's V0 gate did this for E1-1 only (D13 SUMMARY, "Reproduction gate: PASS").
5. **Records** go under `experiments/D14_noslip_rest_rehearsal/results/stage2/<arm>/<exp>/<tid>.json.gz`
   (exclusive create; resume skips existing records). They carry `rec["er9"]` from `er9g_run.run_one` plus
   `apply_verdict` for PG arms, and ER7's fields for L0.
   - `er9g_run`'s own `probe` mode is **not** used: it writes into ER9's results and refuses any other root.
   - Seeds are checked with `er9g_run.check_seed` (l.186–196), which refuses 10000–10999 and 17000–17999.

### 3.5 What NoSlip acts on in this model (`FACT` where cited; MuJoCo source read 2026-11-23, see the note below)
**Model facts** (`src/rubiknetic/cube_physics/m1_model.py`):
- Cubie–cubie contacts: friction (0.2, 0.0025, 0.0005), `condim` 3 (l.52–53).
- Pad geoms: friction (0.8, 0.005, 0.0001), `condim` 4 (l.76–77).
- Cubie joints: `frictionloss` 0.0005 (l.58, written at l.141 and l.145).
- Turner hinges: `damping` 0.01 and no frictionloss (l.181).
- Pad slides: damping only (l.170–171).
- Actuators:
  - grip: `position`, kp 2000, forcerange ±grip_force (l.176–177);
  - turn: `position`, `turn_kp` 5, `turn_kv` 0.2, forcerange ±1 N·m (l.82–84, l.187–188).
- Elliptic cones, `impratio` 10, Newton (l.90–92).
- Pad–cubie contacts are generated: pad contype 2 against cubie conaffinity 3 (l.202, l.207).
- `UNVERIFIED` this session: MuJoCo takes the larger `condim` when two geoms of equal priority meet, so pad–cubie
  contacts would be `condim` 4, with torsional friction.

**What the NoSlip pass does** (read through a fetch-and-summarise tool from
`raw.githubusercontent.com/google-deepmind/mujoco/4.0.1/`; the wording and line numbers must be re-checked against
the raw files before this protocol is fixed):
- `doc/computation/index.rst`, "NoSlip": after the main solver, it "re-solves the friction dimensions only, using a
  PGS sweep with R = 0 (i.e., hard constraints) in those dimensions", and is "an ad-hoc correction that can
  occasionally cause instabilities in models with complex multi-contact interactions".
- `src/engine/engine_solver.c`, the NoSlip routine:
  - one sweep over the **dry-friction rows** (`ne … ne+nf`, i.e. joint/tendon `frictionloss`);
  - one sweep over the **contact friction rows**. For elliptic contacts this covers rows `i+1 … i+dim−1`, which are
    the tangential rows **and** the torsional/rolling rows. The normal force `force[i]` is held fixed, and the
    friction forces are projected onto the cone by a QCQP.
- `doc/XMLreference.rst`: `noslip_iterations` default 0; `noslip_tolerance` default 1e-6.

**Consequences for Stage 2** (`INFERENCE` from the above):
- **Cubie–cubie contacts:** both tangential rows become hard (stick when the solution lies inside the cone). Sliding
  contacts remain bounded by μ·f_n, because the cone projection is unchanged.
- **Pad–cubie contacts (`condim` 4):** the two tangential rows **and** the torsional row become hard. The grip should
  slip and creep less under turner torque. D12 §2 item 3 recorded pads slipping during W3's stall, with pad contacts
  dropping from 10 to 4.
- **Cubie joint `frictionloss` (0.0005 N·m):** this is a dry-friction row, so it is also made hard.
- **Not changed directly:**
  - contact normal forces, so penetration is not changed directly;
  - joint limits;
  - the magnet callback (passive force);
  - the actuator laws: `turn_kp`, `turn_kv`, the 1 N·m clip, grip kp and grip forcerange are actuator forces, not
    constraints.
- **Changed indirectly:** the delivered turner torque (`actuator_force`, logged at `rig.py` l.141) changes only
  through the changed motion (the PD error).

---

## 4. Cost estimate

### 4.1 Inputs (`FACT`)
- **Source:** a read-only Python script, run in this session, decompressed every committed record and summed
  `er7_wall_s`. That field is the time of `E7.run_one` (`er7_run.py` l.149, l.167); for E1-2, E1-5 and E1-5s it is
  within about 1 % of `wall_s`.
- **Load at measurement:**
  - Part G probe: 6 workers (`results/hybrid_g/probe/cost_check_25_PG8.json`, `"workers": 6`);
  - ER7: 8 workers (PROTOCOL §G.11).

**Summed `er7_wall_s` over the Stage 2 trials (s):**

| Arm | E1-2 (24) | E1-5 (42) | E1-5s (20) | Sum (s) | Sum (h) |
|---|---|---|---|---|---|
| PG8 (probe) | 832.8 | 1876.7 | 977.4 | 3686.9 | 1.024 |
| PG20 (probe) | 970.4 | 2217.9 | 1209.6 | 4397.9 | 1.222 |
| L0 (ER7) | 477.9 | 962.4 | 444.4 | 1884.7 | 0.524 |
| All three | | | | 9969.5 | 2.769 |

- Longest single trial: PG20 E1-5s at 160.2 s.
- For reference, E1-1 `er7_wall_s` sums (not part of Stage 2) were PG8 14999.8 s, PG20 17821.5 s and L0 7232.8 s.

### 4.2 Projection with D13's NoSlip factor 1.14–1.26 (D13 SUMMARY, "V2 cost") (`INFERENCE`)

| Arm set | Summed × 1.14 | Summed × 1.26 | Wall at 4 workers (sum ÷ 4), × 1.14 / × 1.26 |
|---|---|---|---|
| PG8 | 3686.9 × 1.14 = 4203.1 s (1.17 h) | 3686.9 × 1.26 = 4645.5 s (1.29 h) | 0.29 / 0.32 h |
| PG20 | 4397.9 × 1.14 = 5013.6 s (1.39 h) | 4397.9 × 1.26 = 5541.4 s (1.54 h) | 0.35 / 0.38 h |
| L0 | 1884.7 × 1.14 = 2148.6 s (0.60 h) | 1884.7 × 1.26 = 2374.7 s (0.66 h) | 0.15 / 0.16 h |
| PG8 + PG20 | 8084.8 × 1.14 = 9216.7 s (2.56 h) | 8084.8 × 1.26 = 10186.8 s (2.83 h) | 0.64 / 0.71 h |
| **All three** | 9969.5 × 1.14 = **11365.2 s (3.16 h)** | 9969.5 × 1.26 = **12561.6 s (3.49 h)** | **0.79 / 0.87 h** |

- **Tail:** add at most one longest trial, 160.2 × 1.26 = 202 s (about 0.06 h), to the wall time. Total wall time
  for all three arms at 4 workers is then **about 0.85–0.95 h**.
- **Gate trials (§3.4 item 4):** 9 trials at the frozen setting. Using the medians above, about 0.1 h summed.
- **Caveats** (`INFERENCE`):
  - D13's factor was measured on 60 s **rests** (8 cases). Turning trials have more contacts, including `condim` 4
    pad contacts and sliding layers, so the factor may be larger.
  - D13's own pre-run assumption was 2× (D13 PROTOCOL §3). At 2×, all three arms come to 19939.0 s summed (5.54 h),
    or **1.38 h** wall at 4 workers.
  - Per-trial wall time depends on machine load. The frozen times were taken at 6 and 8 workers, so 4 workers should
    if anything be faster.
- **Cost stop:** the value is OPEN-3. It needs a number from the user, or the reuse of an existing rule.

---

## 5. Risks and predictions (`INFERENCE`; written before any run)

1. **Turning torque.**
   - Mechanism: NoSlip does not alter the actuator law. The turning layer's sliding contacts stay bounded by μ·f_n,
     so the friction ceiling on the turning layer is unchanged.
   - What changes:
     - the non-turning layers stick harder (expected to reduce non-target drift);
     - the pads stick harder, including torsionally, so less turner motion is lost to pad slip.
   - Prediction: median E1-2 turner torque changes modestly in either direction. The 0-at-clip count is the item most
     at risk for PG20 (frozen p99 0.863 N·m; 19 of 24 moves already above 0.5 N·m).
   - D13 SUMMARY, "Interpretation" item 4: "The harder setting also changes the turning trials, and could raise
     turning torque or cause stalls."
2. **Stalls** (D12 question; `experiments/D12_turn_stall/PROTOCOL.md` §1, §5):
   - D12 asks whether the catch about 7° into a quarter turn depends on contact parameters. One of its premises is
     "contact softness is on the scale of the clearance, so contact parameters are a plausible factor" (§2 item 2).
   - D12 has not been run (commit `9887d68`: "nothing run"; no `results/` folder).
   - Two possible effects of hard friction:
     - it could deepen the catch, because a corner wedged against side-centre contacts at about 45° normals can no
       longer creep through;
     - it could shorten the catch, because the pads transmit more torque before slipping.
   - The direction is not predicted.
   - Limit: the probe records keep per-move peaks only. Stage 2 can see clip counts, turn errors and failed moves, but
     not D12's "stall" class (layer advance < 0.05° over ≥ 30 ms) unless a read-only per-step log is added (OPEN-4).
3. **NoSlip instability with many contacts.**
   - D13 PROTOCOL §1 quotes MuJoCo `doc/modeling.rst` at 4.0.1: NoSlip "adds computational cost, makes inverse
     dynamics ill-defined and can occasionally cause instabilities in complex multi-contact systems".
   - D13 saw none in 50 rest runs (largest solver iteration count 19, no aborts; D13 SUMMARY "V2 cost"). Rest is the
     easiest case.
   - Turning and forgiveness trials have pads (`condim` 4), sliding layers and the E1-5 wedge, so the risk is higher
     there.
   - Detection:
     - `AuditedSim.step` raises `NumericalFailure` only on MuJoCo's fatal warnings (`rig.py` l.83–90). Such trials
       fail under §2.1.
     - Non-fatal jitter would not be flagged. It would appear only through penetration, radial-pop or causality
       criteria, or as odd torque peaks. A read-only solver-iteration log (D10's `StepLog`, `d10_rest.py` l.55–71)
       would help (OPEN-5).
4. **Snap-back (signal 1).**
   - Frozen errors after 1 s: 0.105° (PG8), 0.032° (PG20), 0.118° (L0), against a 0.5° limit.
   - Rest creep rates under the frozen setting were 7–84 mdeg/s (D13 PROTOCOL §1), so soft-friction creep can
     account for at most about 0.08° in the 1 s window.
   - With NoSlip, a layer can stop wherever the magnet restoring torque falls below static friction (a dead band)
     instead of creeping in.
   - Prediction: errors change by less than about 0.1°, and signal 1 is still met by both PG arms. The small-δ
     starts (±1°, ±2°, unscored) are the most likely to stop short.
5. **E1-2 turn error and drift.**
   - Prediction: non-target drift falls.
   - Turn error could grow slightly if the layer sticks short after the pads open (the 2° limit leaves wide margin).
6. **E1-5 forgiveness.**
   - Outcome categories may shift between completed, no net move and blocked/UNKNOWN. All of these are allowed.
   - The categorical failure (illegal or oracle-mismatched transition) is not expected to become more likely, but a
     numerical failure in the wedge would fail the trial (item 3).
7. **Validity (signal 4).**
   - The PCon tilt near 18.4° (frozen max 18.416° in PG20, limit 20°) is set by geometry: the rigid-turn value is
     18.371° (P1).
   - Prediction: met. Friction changes trajectories, not the geometric tilt of the piece-to-core pair.
8. **Cost.** The NoSlip factor on turning trials may exceed 1.26 (§4.2 caveat).

---

## 6. Open questions for the user

- **OPEN-1, arms.**
  - P-73 says Stage 2 is "for arms that pass" Stage 1.
  - Should L0 also run as a same-setting reference even if it misses Stage 1? Cost about 0.60–0.66 h summed, about
    0.16 h wall.
  - Without L0, the noslip turner torque of PG8 and PG20 has only a frozen-setting L0 to compare against.
  - Recommendation: run L0 as a reference in any case, labelled as such.
- **OPEN-2, reproduction gate.**
  - Size: the first trial of each of E1-2, E1-5 and E1-5s per arm (9 trials), or more?
  - Exact equality with the committed records on all physics fields, as GS1 and D13 V0 did, or a stated tolerance?
  - If the gate fails, Stage 2 stops and reports that alone (D13 and D14 precedent).
- **OPEN-3, cost stop.** Which projected total stops the run and returns to you?
  - Options already used: D14's 6 h, or G.7's 24 h probe limit. D13 used 4 h.
  - When to re-project: after the gate batch, and after 25 % of the trials as in G.7?
- **OPEN-4, stall logging.** Add a read-only per-step hook (turner angle and torque, layer angle) on E1-2, so that
  D12's §5 stall and catch classes can be reported?
  - Those rules are D12's, and D12 has not run. Borrowing them is your call.
  - Without the hook, Stage 2 reports only G.8's torque items.
- **OPEN-5, solver logging.** Add D10's read-only `StepLog` (largest solver iteration count, limit hits) to every
  trial, for the instability question (§5.3)? Reported only.
- **OPEN-6, selection.**
  - G.8's selection rule picks, among arms meeting all four signals, the one with the lowest median E1-2 turner
    torque.
  - Should Stage 2 apply it, or only report signals (P-72: no arm selected), leaving any choice to Stage 3?
  - Recommendation: report only.
- **OPEN-7, paired statistics.** Report sign-test counts (frozen against noslip) for per-move torque and snap-back
  error with no pre-set reading, or fix a reading now (as G.8 did for the 60-seed slip comparison)?
- **OPEN-8, a failed trial at NoSlip.**
  - Under §2.1 a numerical failure fails the trial; it is not excluded and not rerun.
  - Should the first such failure also pause the run for you, given the documented instability risk?
- **OPEN-9, where Stage 2 lives.** A new runner and analysis under `experiments/D14_noslip_rest_rehearsal/` (for
  example `d14s2_run.py`, `d14s2_analyze.py`, committed with the fixed protocol before any run), or a new folder
  (D15)?
- **OPEN-10, deferred items stay deferred?**
  - The U5 rest extension (16700–16739) and the P-70 follow-up probe (P-73 item 4).
  - Seeds 17000–17999 and 10000–10999 stay untouched in Stage 2.

## 7. Not determined by this draft (`UNVERIFIED` / not checked)
- The MuJoCo NoSlip behaviour in §3.5 was read through a summarising web fetch, not quoted from the raw files with
  line numbers. In particular, it was not checked whether the dry-friction sweep covers ball-joint `frictionloss`
  rows in exactly the way stated.
- The `condim` combination rule for pad–cubie contacts was not checked in the documentation this session.
- That C1 is the only trial-model compile rests on greps of `src/rubiknetic` and the chain's modules
  (`from_xml_string`, `MjModel.from`, `build_m1_xml`, `MjSpec`, `from_xml_path`, `from_binary_path`). Nothing else was
  found. Runtime proof is the per-record check in §3.4 item 3.
- The NoSlip wall-time factor for turning trials is unknown until measured.

---

## Addendum (main session, 2026-11-23): risks from the NoSlip research, still DRAFT
Source: `docs/research/NOSLIP_AND_CUBE_FRICTION_FINDINGS.md`.
- **FACT.** Every cube piece joint has both `damping` 0.0005 and `frictionloss` 0.0005
  (`src/rubiknetic/cube_physics/m1_model.py`, `M1Params`). MuJoCo issue #2423 (open, reproduced on 4.0.0) reports that
  this combination together with `noslip_iterations` > 0 makes a spinning hinge decelerate far too slowly. The report
  used the `implicit` integrator; D14 uses `implicitfast` (untested). INFERENCE: at rest (D13, D14 Stage 1) this cannot
  show, because nothing spins; during and after a turn it could change overshoot, snap-back and settling.
- **OPEN-11 (proposed check before any Stage 2 trial).** A free-decay check: spin one centre and one corner joint with
  the rig open, at `noslip_iterations` 0 and 10, and compare decay times. If NoSlip slows the decay markedly, Stage 2's
  turning results would be confounded, and the user decides how to proceed.
- **OPEN-12, iteration count.** MuJoCo's documentation says 1–3 iterations are usually enough. D13 and D14 tested 10.
  Changing the value now would be more tuning after the fact. Recommendation: keep 10 and log the NoSlip iteration count
  actually used.
- **Watch items.** Pad "chatter in overconstrained grasps" (documentation), breakaway torque of the turned face, and
  energy and angular momentum across a turn. NoSlip leaves equality rows unsolved (#2430); the cube model uses no
  equality constraints for connectivity (pieces are ball and hinge joints), so this is noted only.
