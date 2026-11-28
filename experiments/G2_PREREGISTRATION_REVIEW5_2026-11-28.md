# G2 pre-registration review 5 (2026-11-28)

VERDICT: ACCEPTABLE AS IS

*(Independent reviewer subagent, round 5 (P-121). It was given the pre-registration, the code, the evidence and
reviews 1–4, not the assistant's conclusions. The report is saved as returned.)*

## Scope and what I ran
I reviewed DRAFT revision 5 at HEAD `ad08a50`. I read it against `E8_scored_g2/{run,trials,analyze,selfcheck,rerun_crashed}.py`, `D18/{two_arm,layout}.py`, `D17/{hold,turn}.py`, `src/rubiknetic/cube_physics/{magnets,rig}.py`, the E4/E5/E7 magnet and parameter code, `tests/test_scored_g2.py`, the pilot-4 records, README and verdict, the rev-5 self-check log, DECISION_LOG P-130 to P-132, and review 4. Nothing in the repository was changed. My scratch scripts are in the session scratchpad and their outputs are in WSL `/tmp/rev5_*`. No scored seed was simulated.

What I ran:
- **Unit tests:** `pytest -q tests/test_scored_g2.py`, **62 passed**.
- **Physics code since pilot 4:** `git diff eb90291 ad08a50`. Only docstrings changed in `trials.py` and `analyze.py`, plus the self-check references and docs. No change to physics code (`FACT`).
- **Scene vs §1:** a probe comparing the cube in `two_arm.build()` with the standalone M7 cube XML (free core added).
  - All `MjOption` fields compared, including disable/enable flags, `noslip_tolerance`, `ls_iterations` and `ccd_iterations`.
  - Every cube geom (friction, solref, solimp, condim, margin, gap, priority, contype, size, pose), body (mass, inertia, pose, gravcomp), joint/DOF (damping, frictionloss, armature, range) and mesh vertex.
  - The cube XML has no pair, exclude or equality elements that attaching could drop.
  - `M1Params` compared with G1's M7 nominal, and `MagnetParams` with G1's nominal.
- **Pilot-4 recount:** every number stated in §0.3, §0.4, §4.1, §4.3, §7 and §8 item 8, from the 144 committed records.
- **Six magnets-on probes at HEAD (pilot seeds)**, with the magnet system's own internal stats exposed by a monkeypatch: `U_s29500`, `Up_s29530`, `U2_s29550`, `jam_s29610`, `two_layer_s29620`, `seq5_s29650`.

## Review-4 items
| # | Status | Evidence |
|---|---|---|
| N1 magnets off | **FIXED** | See the N1 detail below the table. |
| N2 verdict re-run | **FIXED** | Prereg §6 lines 371-375: any INVALID that comes from reading a file must reproduce on a re-run, and every verdict run is reported. |
| N3 move count | **FIXED** | Recount (`FACT`): 244 turn moves in 120 turn trials, negative cases and holds excluded. Causality gaps: minimum 3 steps, then 4, 4, 5, 5…; median 27. This matches §4.1 lines 228-230. |

**N1 detail.**

Code:
- The callback is re-installed after arm B's IK model is built (`two_arm.py:442`). No `robot_spec`/`compile` call follows it on the trial path.
- A counting wrapper replaces `ms.apply` (`:404-410`). `install()`'s lambda looks up `self.apply` at call time (`magnets.py:697-698`).
- Every `ctrl_step` counts a step without an evaluation (`:596-600`). Every simulation step on the trial path goes through `ctrl_step`: `sim.step` appears only at `:597`, and nothing calls `ms.apply` directly.

Records and checks, per trial kind:
- seq, sens and neg: `run()` stores the stats in `trial.magnets` at the end of the trial (`:900`).
- hold: stored after the 60 s loop (`trials.py:201`).
- The worker judges it in `trials.py:114-116`. Negative trials go through `neg_outcome` → `_integrity_reasons`.
- The independent verdict judges it in `analyze.py:51-53`, applied by `recompute_seq`, `recompute_hold` and `recompute_neg`.
- Tests: `test:377-393` (real scene, with a positive control that removes the callback) and `:466-468` (synthetic).

Data (`FACT`):
- All 144 pilot-4 records have `steps_without_magnet_force` = 0.
- In all 144, `steps` = `sim_time_s`/dt exactly, so no step went uncounted. Holds have 127,200 steps.
- In all 144, `force_evaluations` − `steps` = 3: the 3 setup `mj_forward` calls.
- My probes: `MagnetSystem.stats["calls"]`, an independent counter inside the force law, equals `force_evaluations` in all six.
- All six probes are **bit-identical** to the committed pilot-4 records (`final_qpos_sha256`) at HEAD.
- §0.1a, §0.3, §0.4, §4.1 and §7 match the recount, among them:
  - t0 offset 2.252 mm (`U2_s29556`), mean 1.012, sd 0.491, n 142; stand-drop shift ≤ 0.123 mm;
  - first-turn F/T max 0.373 N·m; U′ max 0.373; extreme-misalignment group max 0.334;
  - per-move core rotation 1.209° (mean 0.321°, sd 0.194°, 3 moves above 1°); total rotation 1.120°; total slip 0.626 mm;
  - turn error 0.310°; drift 0.305°; F/T at the frozen configuration 0.485 N·m;
  - end misalignment 0.61–1.05° (n = 16);
  - jam 37.3–44.3°, slip ≤ 0.221 mm; two_layer detected at 1.10–1.15 N·m after 3.4–3.7°;
  - holds: slip ≤ 0.132 mm, rotation ≤ 0.315°.

**Other N1-class differences: none found (`FACT`).**
- The cube and solver options in the two-arm scene are identical to the standalone M7 cube (0 differences).
- `M1Params` differs from G1's M7 nominal only in `rig=False`, which is intended.
- The magnets are 4×2 mm N35 with a 0.4 mm wall, which equals G1's nominal face gap of 0.85 mm.

## New findings

**S1. SUGGESTED (the most relevant one): G1's magnet-validity rule is neither recorded nor judged in G2.**
- G1-scored M7 failed an operational trial when the near-pair tilt exceeded the validated 5° (`PHASE_1_M7_PREREGISTRATION.md:252`; `E4/run.py:476-483`). The force law also needs `near_perpendicular` = 0 (`magnets.py` docstring).
- §1 says "M7 as G1-scored". The G2 records store only call counts (`two_arm.py:602-605`), so the per-step check shows that the force was evaluated, not that it stayed within its validated range.
- Probe (`FACT`, pilot seeds): `max_near_tilt_deg` was 1.39 (U), 1.82 (U′), 1.22 (U2), 1.21 (jam), 1.53 (two_layer) and 1.67 (seq5); `near_perpendicular` and `clamped_z` were 0. The risk of a false PASS is therefore low (`INFERENCE`).
- Fix: add `max_near_tilt_deg`, `near_perpendicular` and `clamped_z` from `self.ms.stats` to `magnet_stats()`. Then either judge tilt ≤ 5° and `near_perpendicular` = 0 in both `trials` and `analyze`, or disclose in §0.6/§8 that G1's rule 2 is not applied.
- If the keys are added: `selfcheck.physics()` compares the whole `magnets` dict (`selfcheck.py:53`). Compare only the three existing keys, or the pilot-4 references will show DIFFERS. The physics itself is unchanged, because the stats are diagnostics only.

**S2. SUGGESTED: §0.4 understates the tightest judged margin.**
- §0.4 (lines 69-70) says the t0 offset is the closest value at 75 % of its limit and that "every other is at most 61 %".
- The scored `jam` case (2 trials) stopped at up to 44.3° against a 50° upper bound: 89 % of the bound, 5.7° of headroom (`FACT`; 6 pilots, mean about 40.9°).
- Fix: state the jam-window headroom in §0.4 and in §8 item 8.

**S3. SUGGESTED: the §4.3 text omits the magnet check.**
- Lines 249-250 list abort, edit-audit, numerical, harness and model-audit failures. The code also fails a negative trial on the magnet check (`trials.py:245-246` → `:114-116`).
- The code is stricter than the text, so this cannot cause a false PASS. Add "or the magnet check".

**S4. SUGGESTED: harden the step count.**
- `magnets.steps` counts `ctrl_step` calls, not `AuditedSim.steps`. Today they are equal (`FACT`, all 144 records), but a future direct `sim.step` would not be counted.
- Fix: record `sim.steps` and require `magnets.steps == sim.steps`. In `analyze`, also require `steps == round(sim_time_s / 0.0005)`.

**S5. SUGGESTED: self-check provenance.**
- The rev-5 log says its HEAD hash "was lost by the logging command and is filled in from git log". `selfcheck.py` does not print HEAD.
- My HEAD probes reproduce six pilot-4 records bit-identically, so the claim holds.
- Fix: have `selfcheck.py` print `git rev-parse HEAD`, and re-run it at the freeze commit.

**S6. SUGGESTED: the verdict outputs are overwritten.**
- §6 calls the verdict "read-only", but `analyze.main` writes `VERDICT.md` and `verdict.json` next to `results/` (`analyze.py:399-400`) and overwrites them on every re-run. "Every verdict run is reported" relies on the operator keeping each output.
- Fix: write a timestamped file per run, or say so in §6.

## Checked with no problem found
- **Controllers vs §2:**
  - J7 law, feedforward and budget B = 2 + 0.2(|2q̇| + 1);
  - impedance gains; integral term only while open (held while gripping);
  - F/T guard: 200 Hz (every 10 steps), noise 0.01, stop after two samples above 1.0 N·m;
  - stall rule 2° / 20 ms; move timings; approach.
- **Scene vs §1:** fingertip sizes (P-97 30×30×4 mm; C1 25×4×14 mm half-sizes ×2); time constant 0.01 s on both arms; 20 N grip; stand drop 30 mm; visuals off in `configure`; arm layout.
- **Integrity and verdict machinery:**
  - load-error phase rule (the magnet refusal raises before the first step);
  - resume limits; the ledger, manifest and start-log checks;
  - artifact hashing of the magnet table actually loaded (`_tables_for` → `table_path`);
  - frozen paths match the text.
- **Counts:** 138 trials / 128 scored; Clopper–Pearson on 100 turn trials.
- **Seed search:** only `tests/test_scored_g2.py` contains 30xxx seeds.
- **Holds:** the magnet stats cover the whole 60 s; an abort fails the trial through the missing stats or `aborted`.
- **Worker vs verdict:** `_integrity_reasons` and `analyze._integrity` agree on the magnet rule (missing dict, `steps` = 0, nonzero missing count). Both copies are tested.
- **Pilot-4 verdict:** PASS with clean integrity; the start log shows one clean resume.
