# D13 — Unscored diagnostic of the rest slip events (PROTOCOL, fixed before any run)

**Status:** approved by the user 2026-11-23 (P-72: "okay now, begin working on it", in reply to the draft in
`experiments/ER9_anchored_core_layouts/proposals/D13_SLIP_DIAGNOSTIC_DRAFT.md`). This file is committed with
`d13_run.py` and `d13_analyze.py` **before** the first D13 run, so the commit date shows that the questions, the runs
and the reading rules were fixed in advance. Section 7 lists the changes from the draft, all made before any run.

**Scope (`FACT`):** UNSCORED, reported only.
- M5 stays NOT PASSED (P-51). Part G's probe outcome stays as reported (no arm selected; P-72).
- No threshold changes.
- D13 writes only under `experiments/D13_rest_slip_mechanism/`. It does not edit `src/`, any scored runner, ER7, or
  anything under `experiments/ER9_anchored_core_layouts/`, so Part G's gates stay valid.
- Seeds: rehearsal seeds 16000–16999 only, and only the six listed in section 3 (16000, 16003, 16005, 16011, 16013,
  16016).

## 1. Background
`FACT` unless marked. Source for every number in this section: the committed 60 s rest records, read by
`experiments/ER9_anchored_core_layouts/side_checks/slip_anatomy/slip_anatomy.py`, output `slip_anatomy_out.txt` in
the same folder (read-only, post hoc, written after the probe report; commit `15b4e88`).

- **Event definition (D11, unchanged):** a piece's rotation about one of its face normals changes by ≥ 0.2° within
  200 ms, at 25 ms samples.
- **Six events in 80 records.** PG8: seeds 16003, 16011, 16016. PG20: seed 16013. L0 (ER7): seeds 16003, 16005.
  C52 (ER7): none.
- **Events are separate from the background.** In PG8, PG20 and C52, the largest 200 ms change in a seed is either
  ≥ 0.205° (the four events) or ≤ 0.096°. L0 has one seed between the two, at 0.115°.
- **Each event has two stages.**
  - The piece first drifts in one direction for 1.0–15.3 s, reaching 0.095–0.174°. The least-squares rate is
    6.7–7.6 mdeg/s in the three late hybrid events, 22–35 mdeg/s in L0, and 84 mdeg/s in PG8 16016.
  - It then moves 0.205–0.400° within 200 ms (largest 25 ms step 0.073–0.176°), together with one or two neighbours.
  - The magnet energy falls throughout.
- **Size.** 0.205–0.242° in PG8 and PG20; 0.390–0.400° in L0.
- **Place.** The leading piece of all six events is in the row shared by the U and F layers (`nnp`, `0np` or `pnp`;
  U is +z, F is −y). Five turn about U, one (PG20) about F.
- **Magnet torque.** In PG8 and L0 the leading piece carries one of the three largest net magnet torques
  (8.1–14.4 mN m at the event). In PG20 it does not (1.7 mN m, rank 12 of 21).
- **Drift without events.** In seeds without an event, the largest net change from the first to the last sample is
  0.043–0.227° (PG8), 0.034–0.218° (PG20) and 0.098–0.345° (L0). In C52 it is 0.000° in all 20 seeds.
- **Earlier work on L0.**
  - D10 (P-53): a finer timestep changed the event's timing but not its size, and 400 solver iterations gave
    bit-identical results.
  - ER1 (P-54): a slip is a corner-and-edge cluster crossing a consolidated gap. At the aligned pose, M5's
    single-piece magnet stiffness is negative.
  - Neither changed the friction settings.
- **Model.** Each edge and corner is a body on a ball joint at the cube centre (`src/rubiknetic/cube_physics/m1_model.py`).
  Contacts: friction 0.2, `condim` 3, `solref` (0.001, 1), `solimp` (0.95, 0.99, 0.0005), elliptic cones,
  `impratio` 10, Newton, 100 iterations, tolerance 1e-10, `noslip_iterations` 0.
- **Simulator documentation** (MuJoCo `doc/modeling.rst`, subsection "Slow slippage" and section "Solver settings";
  read 2026-11-23 from the repository at tag `4.0.1`, the installed version, through the GitHub API; Apache-2.0).
  - Verbatim: "Even when the tangential force required for static equilibrium lies strictly inside the contact
    friction cone, MuJoCo's regularized soft-contact model does not guarantee an exact zero-velocity stick state. In
    the recommended elliptic contact model, friction dimensions have no position residual and are purely damped, so a
    persistent tangential load can produce a nonzero steady slip velocity. This is expected behavior".
  - Remedies (paraphrased):
    - (a) elliptic cones with a larger `impratio`, which "makes the friction dimensions harder relative to the normal
      dimension without increasing the friction coefficient";
    - (b) the NoSlip post-processing solver (`noslip_iterations` > 0), for which "A small number (1, 2 or 3) is usually
      sufficient" and "Exact zero slip is not guaranteed".
  - Costs noted: NoSlip "adds computational cost, makes inverse dynamics ill-defined and can occasionally cause
    instabilities in complex multi-contact systems".
  - The source does not establish that the drift in these records is this effect.
- `INFERENCE`: a piece held by Coulomb friction should either hold or move, not drift for seconds. The drift may be
  the simulator's soft friction. If it is, it feeds the events; the events themselves (crossing a gap) may still be
  the model's own behaviour.

## 2. Questions (fixed)
> **Q1.** Is the slow drift that precedes each event produced by the softness of the friction constraints, or does it
> persist when friction is made harder?
> **Q2.** Do the events still occur when the drift is suppressed?
> **Q3.** Why is the leading piece always in the U∩F row: gravity, the order in which the setup misaligns the
> layers, or neither?
> **Q4.** At the contacts of the drifting piece, is the friction force at the cone limit (true sliding) or inside it
> (soft-constraint creep), and what changes at the moment of the event?

## 3. Runs
**Cases.** In every case the reference piece, its axis and `T_ref` are computed by `d13_analyze.reference()` from the
committed record; the table shows them rounded.
- **Slip cases.** The reference piece and axis are those with the largest 200 ms change in the record (the event's
  leading piece). `T_ref` is the start of that 200 ms window.
- **Quiet cases.** The reference piece and axis are those with the largest net change from the first to the last
  sample, and `T_ref` is the last sample (60 s). For each hybrid arm, the quiet case is the lowest seed whose largest
  200 ms change is < 0.05°.

| Case | Arm | Seed | Piece / axis | `T_ref` (s) | Committed event size (°) |
|---|---|---|---|---|---|
| C1 | PG8 | 16003 | `nnp` / U | 15.30 | 0.242 |
| C2 | PG8 | 16011 | `0np` / U | 15.10 | 0.205 |
| C3 | PG8 | 16016 | `0np` / U | 1.02 | 0.232 |
| C4 | PG20 | 16013 | `pnp` / F | 13.88 | 0.240 |
| C5 | L0 | 16003 | `nnp` / U | 5.27 | 0.400 |
| C6 | L0 | 16005 | `pnp` / U | 7.30 | 0.390 |
| Q1 | PG8 | 16000 | `0np` / U | 60 | none |
| Q2 | PG20 | 16000 | `npn` / L | 60 | none |

**How a run reproduces the committed trial.** Each run is a fresh worker process. It repeats the steps that produced
the committed record:
- **Arm installation.** PG8 and PG20 are installed with `er9g_layouts.install_er7(arm, "N52")` and the class-stats
  system, as `er9g_run.run_one`. L0 uses ER7's own path.
- **Warm-up.** ER7's 10 s scored-format rest trial (`er7_run.run_one` with the 60 s rest switched off) runs first,
  at the frozen settings. It is recorded but not analysed.
- **The 60 s rest,** as ER7 sets it up: `use_magnets`, then reset of the neighbour list and stats, then
  `MagnetMonitor.last = None`. The rest is D13's instrumented copy of `d10_rest.instrumented_rest`, with the same
  loop, metric and logging, plus the logging below.

The variant applies only to the 60 s rest.

**Variants.** Each changes one thing from the frozen settings.

| Variant | Change | Cases | Purpose |
|---|---|---|---|
| V0 | none | all 8 | Exact reproduction; the added logging is read-only |
| V1 | `impratio` 100 (from 10) | all 8 | Q1, Q2: friction 10 × harder relative to the normal direction |
| V2 | `noslip_iterations` 10 (from 0) | all 8 | Q1, Q2: friction made hard after the main solve |
| V3 | timestep 0.25 ms (from 0.5 ms) | all 8 | Integration error (D10's A1, now on the hybrids). Reported only |
| G1 | gravity 0 | C1–C6 | Q3 |
| G2 | gravity +9.81 m/s² along z (flipped) | C1–C6 | Q3 |
| S1 | the six setup misalignments applied in reverse face order (B, L, D, F, R, U), same angles | C1–C6 | Q3 |

That is 50 runs.

**How each variant is applied:**
- V1, V3, G1 and G2 go through `scored.params_for` (fields `impratio`, `timestep`, `gravity_z`).
- V2 adds `noslip_iterations="10"` to the model's `<option>` element while the trial model is compiled (a wrapper
  around `scored.build_m1_xml`, restored right after).
- S1 reverses the order of the drawn setup's misalignment dictionary.
- Each record stores the compiled model's `timestep`, `impratio`, `noslip_iterations` and gravity, as proof that the
  variant took effect.

**Cost** (`ASSUMPTION`). The probe took about 690 s of wall time per 60 s rest with six workers. V2 and V3 are assumed
to take twice as long: the documentation says NoSlip roughly doubles the step time, and V3 has twice as many steps.
The total is then about 2.5 hours with six workers.

**Cost stop.** After the V0 batch, the runner projects the total from the measured V0 times, using the same factors.
If the projection exceeds 4 hours, D13 stops and reports.

**Memory.** Workers are reduced if less than 2 GB of memory would remain free. Runs killed for low memory are not
restarted without the user's instruction.

**Logged in every run** (read-only).
- Every 25 ms of simulated time, at the same sample times as the committed records:
  - everything `instrumented_rest` logs;
  - per piece (all 26 bodies), at the sample instant: the number of contacts, the summed normal force, the largest
    friction-cone use `|f_t| / (μ f_n)`, and the largest tangential slip speed at its contacts;
  - per piece, the cumulative contact sliding distance, split into the part accrued while cone use < 0.95 ("creep")
    and the part at ≥ 0.95 ("sliding"), accumulated every 2.5 ms (slip speed × 2.5 ms).
- Contact forces and velocities are read in the contact frame from `efc_force` and `efc_vel`, which elliptic cones
  give directly. The runner checks this on the first sample against `mj_contactForce`. They are the values of the
  last solver pass inside `mj_step`.

**Event capture.** A rolling buffer keeps the last 1 s at 2.5 ms intervals: all joint positions and, per contact, the two
geoms, the distance, the contact-frame force (normal and two tangential), the contact-frame velocity and μ. At the
first event (D11's definition, checked at every 25 ms sample), the buffer is saved together with the following 0.5 s.
One capture per run.

**Code.** `experiments/D13_rest_slip_mechanism/d13_run.py` and `d13_analyze.py`, committed and clean before any run;
the runner refuses otherwise. Before the first run, a code smoke of 1 s simulated time may run with output outside the
repository; it is not compared with anything and is not a result. Environment: WSL `~/.venvs/rubiknetic`
(MuJoCo 4.0.1), as the probe.

## 4. Measures (fixed)
- **Event:** D11's definition, on any piece, within 60 s (`d11_analyze.events`).
- **Leading piece of a run:** the piece and axis with the largest 200 ms change in that run.
- **Drift ratio ρ** (V1–V3 only):
  - Definition: |change of the reference piece's angle about the reference axis from the first sample to the sample
    at `T_ref`| in the variant, divided by the same quantity in V0.
  - If the variant has an event on any piece that starts before `T_ref`, ρ is not computed and the run is marked
    "earlier event".
- **Per-run label** (slip cases, V1 and V2):
  - *suppressed*: ρ ≤ 0.25 and no event in 60 s;
  - *persists*: an event in 60 s (including "earlier event"), or ρ ≥ 0.5;
  - *intermediate*: anything else.
- **Creep share** (Q4, V0, reported only): the reference piece's creep distance at `T_ref` divided by its creep plus
  sliding distance at `T_ref`.

## 5. Gate and reading rules (fixed)
**Reproduction gate.** For all 8 cases in V0:
- the 0–10 s rest rotation must equal the committed record's `rest60` value exactly;
- every `rot_deg` sample must match the committed series to 1e-9°.

If not, D13 stops and reports that alone.

**Rule for Q1 and Q2** (over the six slip cases):
1. **Drift is mostly numerical, and the events depend on it:**
   - V2 is *suppressed* in at least 5 of 6;
   - V1 has ρ ≤ 0.5 in at least 5 of 6;
   - neither V1 nor V2 has an event in Q1 or Q2.

   **Next step (`PROPOSAL`, the user decides):** a proposal for a rest rehearsal of PG8 and PG20 on all 20 seeds at
   the harder friction setting. Adopting any such setting would need a re-validation of the earlier model checks at
   that setting, and a new pre-registration with new seeds, disclosed as chosen after M5 and Part G failed.
2. **Model behaviour:** V1 is *persists* in at least 5 of 6, and V2 is *persists* in at least 5 of 6. **Next step:**
   design options go to the user (for example weaker corner-and-edge magnets with the core pairs kept, or less piece
   play); no retuned rerun.
3. **Anything else is inconclusive:** reported, and the user decides. This includes V1 and V2 disagreeing, and a
   variant that creates an event in a quiet case.

**Predictions, written before any run (`INFERENCE`):**
- If the drift is soft-friction creep: ρ ≈ 0.1 in V1, ρ ≈ 0 in V2, ρ ≈ 1 in V3, and the creep share is above one
  half.
- If it is true sliding: ρ ≈ 1 in V1 and V2, and the creep share is near 0.

**Labels for Q3** (descriptive, not criteria; over the six slip cases):
- *gravity-linked*: G1 has no event in at least 5 of 6, or at least 4 of the G2 runs that still have an event have
  their leading piece in the D layer;
- *setup-linked*: at least 4 of the S1 runs that still have an event have their leading piece outside the U∩F row;
- *not explained*: otherwise.

Both labels can hold.

V3 and the creep share are reported only.

## 6. Limits (fixed)
- Six events on three arms and one set of seeds. D13 can say what drives these events. It cannot say how often they
  occur under any other setting.
- A variant that removes the events is not a fix. It has not been checked on turns, forgiveness or snap-back, and
  NoSlip has the documented costs quoted in section 1.
- Whether a real cube's pieces creep or jump by 0.2° is not addressed. Physical credibility stays unverified.
- D13 is unscored. Its results are `FACT` about these simulations and `INFERENCE` about the mechanism; none is a
  `VALIDATED_RESULT`.
- Changes to this protocol after the first run are recorded as deviations, with the reason, in the D13 summary.

## 7. Changes from the approved draft (made before any run)
1. **Documentation passage.** It was re-read at tag `4.0.1` from the repository source, as the draft required. It is
   quoted verbatim, and the draft's caution about the "stable" web page is replaced.
2. **Reproduction path.** The draft said only that setup follows ER7. It now states ER7's full sequence, including
   the 10 s warm-up trial before the 60 s rest, so V0 can reproduce the committed records exactly.
3. **Definitions made explicit.** ρ uses absolute values, the "leading piece" of a run is defined, and `T_ref` and
   the reference pieces are computed from the committed records rather than read from a rounded table.
4. **Cost estimate.** Raised from about 2 hours to about 2.5 hours, after counting V2 and V3 at twice the time. The
   4-hour stop is unchanged.
5. **Contact reading.** The source of the contact forces and velocities, and its check, are stated. The event capture
   also stores μ.
6. **Code smoke.** A 1 s code smoke outside the repository is allowed before the first run.
7. **Capture interval.** 2.5 ms instead of the draft's 2 ms. The code smoke found that 2 ms (4 steps) does not divide the 25 ms sample (50 steps); 2.5 ms divides it at both timesteps (5 and 10 steps).
