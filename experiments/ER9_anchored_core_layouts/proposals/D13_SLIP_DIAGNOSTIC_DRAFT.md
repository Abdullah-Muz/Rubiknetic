# DRAFT — not approved

> **Superseded 2026-11-23.** Approved by the user ("okay now, begin working on it") and recorded as P-72 in `docs/DECISION_LOG.md`. The fixed protocol is `experiments/D13_rest_slip_mechanism/PROTOCOL.md` (its section 7 lists the changes from this draft, all made before any run). This file is kept unchanged below as the approved draft.

**Status: PROPOSAL, 2026-11-23.** Nothing here is recorded, approved or in force. `docs/DECISION_LOG.md`,
`../PROTOCOL.md` and `../SUMMARY.md` are unchanged, and no D13 simulation has run. Two parts, each needing the user's
approval:
- **Part 1:** a decision-log row (it would take the next free number, P-72; the ER9 record drafted in
  `ER9_RECORD_DRAFT.md` would then take the number after it).
- **Part 2:** the protocol of D13, an unscored diagnostic of the slip events. On approval it is copied unchanged to
  `experiments/D13_rest_slip_mechanism/PROTOCOL.md` and committed with its script before the first run.

Labels: `FACT` (file or commit named), `INFERENCE`, `ASSUMPTION`, `PROPOSAL`. Nothing here is a `VALIDATED_RESULT`.

---

## Part 1. Proposed decision-log row

> | P-72 | **ER9 Part G probe recorded; the P-70 follow-up probe is deferred; D13 slip diagnostic first** (user:
> "okay so now it seems we need to do some trouble shooting", then "yes" to drafting this row and the D13 protocol,
> 2026-11-23). **Probe** (`experiments/ER9_anchored_core_layouts/results/hybrid_g/probe/`, `b0698ba`; rehearsal seeds,
> unscored): 212 / 212 trials complete. No arm meets all four signals. PG8 and PG20 meet signal 1 (snap-back, worst
> 0.105° / 0.032°), signal 3 (E1-2 and E1-5 all pass) and signal 4 (0 trials out of regime), and miss signal 2: fast
> slip events (D11's definition) on 3 / 20 (PG8) and 1 / 20 (PG20) seeds, sizes 0.205–0.242°, with every rest
> rotation ≤ 0.5° (max 0.327° / 0.151°). L0 on the same seeds: 2 / 20. E1-2 turner median 0.378 (PG8) and
> 0.576 N m (PG20). No arm is selected. **Decision.** Interpretation, recorded as such: (1) P-70 item 1 (one PG20
> snap-back diagnostic, then a probe of PG20 at N42 and N35) is **deferred, not run and not cancelled**; it stays the
> only permitted follow-up probe of a new arm unless the user decides otherwise after D13. Disclosed: this was decided
> after the probe result was known, and after the assistant stated its expectation (`INFERENCE`) that weaker core
> magnets would lower the turning torque but not reduce the slips. (2) **D13** runs first: an unscored diagnostic of
> the slip events on rehearsal seeds, its question, runs and reading rules fixed in
> `experiments/D13_rest_slip_mechanism/PROTOCOL.md` and committed before any run. D13 cannot change M5's verdict
> (NOT PASSED) or Part G's outcome, selects no mechanism and no simulation setting; anything chosen from it needs the
> user's approval and a new pre-registration with new seeds, disclosed as chosen after these results. (3) The U5 rest
> extension (rest40, deferred under P-71) stays deferred | **RECORDED / APPROVED 2026-11-23** |

---

## Part 2. D13 — Unscored diagnostic of the rest slip events (PROTOCOL draft)

**Scope (`PROPOSAL`):** UNSCORED, reported only. M5 stays NOT PASSED (P-51). Part G's probe outcome stays as reported
(no arm selected). No threshold changes. D13 writes only under `experiments/D13_rest_slip_mechanism/`. It does not
edit `src/`, any scored runner, ER7, or anything under `experiments/ER9_anchored_core_layouts/` (so Part G's gates
stay valid). Seeds: rehearsal seeds 16000–16999 only, and only those listed in section 3.

### 1. Background
`FACT` unless marked. Source for every number in this section: the committed 60 s rest records, read by
`../side_checks/slip_anatomy/slip_anatomy.py`, output `../side_checks/slip_anatomy/slip_anatomy_out.txt` (read-only,
post hoc, written after the probe report).

- **Event definition (D11, unchanged):** a piece's rotation about one of its face normals changes by ≥ 0.2° within
  200 ms, at 25 ms samples.
- **Six events in 80 records.** PG8: seeds 16003, 16011, 16016. PG20: seed 16013. L0 (ER7): seeds 16003, 16005.
  C52 (ER7): none.
- **Events are separate from the background.** Per seed, the largest 200 ms change is ≥ 0.205° (the six events) or
  ≤ 0.096° in PG8, PG20 and C52. L0 has one seed between, at 0.115°.
- **Each event has two stages.** The piece first drifts in one direction for 1.0–15.3 s, reaching 0.095–0.174°
  (least-squares rate 6.7–7.6 mdeg/s in the three late hybrid events, 22–35 mdeg/s in L0, 84 mdeg/s in PG8 16016).
  It then moves 0.205–0.400° within 200 ms (largest 25 ms step 0.073–0.176°), together with one or two neighbours.
  The magnet energy falls throughout.
- **Size.** 0.205–0.242° in PG8 and PG20; 0.390–0.400° in L0.
- **Place.** The leading piece of all six events is in the row shared by the U and F layers (`nnp`, `0np` or `pnp`).
  Five turn about U, one (PG20) about F.
- **Magnet torque.** In PG8 and L0 the leading piece carries one of the three largest net magnet torques
  (8.1–14.4 mN m at the event). In PG20 it does not (1.7 mN m, rank 12 of 21).
- **Drift without events.** In seeds without an event, the largest net change from the first to the last sample is
  0.043–0.227° (PG8), 0.034–0.218° (PG20) and 0.098–0.345° (L0). In C52 it is 0.000° in all 20 seeds.
- **Earlier work on L0.** D10 (P-53): a finer timestep changed the event's timing but not its size; 400 solver
  iterations were bit-identical. ER1 (P-54): a slip is a corner-and-edge cluster crossing a consolidated gap; at the
  aligned pose M5's single-piece magnet stiffness is negative. Neither changed the friction settings.
- **Model.** Each edge and corner is a body on a ball joint at the cube centre (`src/rubiknetic/cube_physics/m1_model.py`).
  Contacts: friction 0.2, `condim` 3, `solref` (0.001, 1), `solimp` (0.95, 0.99, 0.0005), elliptic cones, `impratio` 10,
  Newton, tolerance 1e-10, no noslip pass.
- **Source on the simulator.** MuJoCo documentation, "Modeling" page, sections "Solver settings" and "Slow slippage"
  (<https://mujoco.readthedocs.io/en/stable/modeling.html>, read 2026-11-23 through an automated page reader; Apache-2.0).
  What it establishes: the soft-contact model does not guarantee a zero-velocity stick state; with elliptic cones
  friction is only damped, so a persistent tangential load can give a steady slip velocity; the remedies named are
  elliptic cones, a larger `impratio`, Newton with a small tolerance, and the noslip pass (`noslip_iterations` > 0).
  What it does not establish: that the drift in these records is that effect. The "stable" page may describe a later
  version than the installed MuJoCo 4.0.1; the exact wording is re-read on the page before this protocol is fixed.
- `INFERENCE`: a piece held by Coulomb friction should either hold or move, not drift for seconds. The drift may be
  the simulator's soft friction. If it is, it feeds the events; the events themselves (crossing a gap) may still be
  the model's own behaviour.

### 2. Questions (fixed)
> **Q1.** Is the slow drift that precedes each event produced by the softness of the friction constraints, or does it
> persist when friction is made harder?
> **Q2.** Do the events still occur when the drift is suppressed?
> **Q3.** Why is the leading piece always in the U∩F row: gravity, the order in which the setup misaligns the
> layers, or neither?
> **Q4.** At the contacts of the drifting piece, is the friction force at the cone limit (true sliding) or inside it
> (soft-constraint creep), and what changes at the moment of the event?

### 3. Runs
**Cases** (arm, seed, reference piece / axis, reference time `T_ref`). For slip cases the reference piece and axis
are the event's leading piece, and `T_ref` is the start of the event's 200 ms window in the committed record. For
quiet cases the reference piece is the one with the largest net change, and `T_ref` = 60 s. Quiet cases are, per
hybrid arm, the lowest seed whose largest 200 ms change is < 0.05°.

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

**Variants.** Each changes one thing from the frozen settings of the committed record (M5's B1 settings, piece gap
0.05 mm; PG8 and PG20 through `er9g_layouts.install_er7` with grade N52, L0 through ER7's own path). Every run is the
instrumented 60 s rest (`d10_rest.instrumented_rest`'s loop and metric, plus the logging below). Setup is drawn from
the seed as in ER7.

| Variant | Change | Cases | Purpose |
|---|---|---|---|
| V0 | none | all 8 | Exact reproduction; the added logging is read-only |
| V1 | `impratio` 100 (from 10) | all 8 | Q1, Q2: friction 10 × harder relative to the normal direction |
| V2 | `noslip_iterations` 10 (from 0) | all 8 | Q1, Q2: friction made hard after the main solve |
| V3 | timestep 0.25 ms (from 0.5 ms) | all 8 | Integration error (D10's A1, now on the hybrids). Reported only |
| G1 | gravity 0 | C1–C6 | Q3 |
| G2 | gravity +9.81 m/s² along z (flipped) | C1–C6 | Q3 |
| S1 | the six setup misalignments applied in reverse face order (B, L, D, F, R, U), same angles | C1–C6 | Q3 |

That is 50 runs. Estimated cost (`ASSUMPTION`, from the probe's 11.4 s of wall time per simulated second with six
workers): about 2 hours with six workers. **Cost stop:** if, after the V0 batch, the projected total exceeds 4 hours,
D13 stops and reports. Workers are reduced if less than 2 GB of memory is free. Runs killed for low memory are not
restarted without the user's instruction.

**Logged in every run** (read-only), every 25 ms of simulated time: everything `instrumented_rest` logs now, plus,
per piece, the number of contacts, the summed normal force, the largest friction-cone use `|f_t| / (μ f_n)` and the
largest tangential slip speed at its contacts. **Event capture:** a rolling buffer keeps the last 1 s at 2 ms
intervals (all joint positions; per contact the two geoms, distance, normal force, tangential force and tangential
velocity). At the first event it is saved together with the following 0.5 s. One capture per run.

Code: `experiments/D13_rest_slip_mechanism/d13_run.py` and `d13_analyze.py`, committed and clean before any run.
`noslip_iterations` is set on the compiled model's options; no file under `src/` changes. Environment: WSL
`~/.venvs/rubiknetic` (MuJoCo 4.0.1), as the probe.

### 4. Measures (fixed)
- **Event:** D11's definition, on any piece, within 60 s.
- **Drift ratio ρ** (V1–V3 only): the reference piece's change in angle about the reference axis from the first
  sample to `T_ref`, divided by the same quantity in V0. If the variant has an event on any piece that starts before
  `T_ref`, ρ is not computed and the run is marked "earlier event".
- **Per-run label** (slip cases, V1 and V2):
  - *suppressed*: ρ ≤ 0.25 and no event in 60 s;
  - *persists*: an event in 60 s, or ρ ≥ 0.5;
  - *intermediate*: anything else.
- **Creep share** (Q4, V0, reported only): over the time before `T_ref`, the share of the reference piece's contact
  sliding distance (slip speed × time, summed over its contacts) that accrues while cone use is < 0.95.

### 5. Gate and reading rules (fixed)
**Reproduction gate.** In V0, for all 8 cases, the 0–10 s rest rotation must equal the committed record's value
exactly, and every `rot_deg` sample must match the committed series to 1e-9°. If not, D13 stops and reports that
alone.

**Rule for Q1 and Q2** (over the six slip cases):
1. **Drift is mostly numerical, and the events depend on it:** V2 is *suppressed* in at least 5 of 6, V1 has ρ ≤ 0.5
   in at least 5 of 6, and neither V1 nor V2 has an event in Q1 or Q2. **Next step (`PROPOSAL`, the user decides):**
   a proposal for a rest rehearsal of PG8 and PG20 on all 20 seeds at the harder friction setting. Adopting any such
   setting would need a re-validation of the earlier model checks at that setting and a new pre-registration with
   new seeds, disclosed as chosen after M5 and Part G failed.
2. **Model behaviour:** both V1 and V2 are *persists* in at least 5 of 6. **Next step:** design options go to the
   user (for example weaker corner-and-edge magnets with the core pairs kept, or less piece play); no retuned rerun.
3. **Anything else is inconclusive:** reported, and the user decides. This includes V1 and V2 disagreeing, and a
   variant that creates an event in a quiet case.

**Predictions, written before any run (`INFERENCE`):** if the drift is soft-friction creep, ρ ≈ 0.1 in V1, ρ ≈ 0 in
V2, ρ ≈ 1 in V3, and the creep share is above one half. If it is true sliding, ρ ≈ 1 in V1 and V2 and the creep share
is near 0.

**Labels for Q3** (descriptive, not criteria; over the six slip cases):
- *gravity-linked*: G1 has no event in at least 5 of 6, or in G2 at least 4 of the events that remain have a leading
  piece in the D layer;
- *setup-linked*: in S1 at least 4 of the events that remain have a leading piece outside the U∩F row;
- *not explained*: otherwise. Both labels can hold.

V3 and the creep share are reported only.

### 6. Limits (fixed)
- Six events on three arms and one set of seeds. D13 can say what drives these events; it cannot say how often they
  occur under any other setting.
- A variant that removes the events is not a fix. It has not been checked on turns, forgiveness or snap-back, and
  the noslip pass has known costs (the documentation notes added cost and occasional instability with many contacts).
- Whether a real cube's pieces creep or jump by 0.2° is not addressed. Physical credibility stays unverified.
- D13 is unscored. Its results are `FACT` about these simulations and `INFERENCE` about the mechanism.
- Changes to this protocol after the first run are recorded as deviations, with the reason, in the D13 summary.
