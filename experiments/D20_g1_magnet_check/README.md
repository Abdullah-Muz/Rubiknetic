# D20: did the magnets act at every step on G1's trial path? (UNSCORED; rehearsal seeds; 2026-11-28)

**Why:** review 4 (P-130) found that the M7 magnets were switched off in every two-arm (D18/G2) trial: building a second
model uninstalled MuJoCo's process-global passive callback. "G1 is not affected" rested on reading the code. The user
asked for a runtime proof.

**How (`g1_magnet_probe.py`):**
- It loads G1's scored runner (`experiments/E7_scored_m7/run.py`, unchanged) and wraps `MagnetSystem.apply` and
  `AuditedSim.step` with counters. A step in which the magnet force was not evaluated counts as "missing".
- It runs three of E7's own self-check jobs in-process, on rehearsal seeds 16000–16300 (never G1's scored seeds
  17000–17739): E1-2 `U_s16100`, E1-4 `sexy6_s16300` and E1-1 `rest_s16000`.
- It compares each record with its committed D15 rehearsal reference (`E7.selfcheck_compare`). 0 differences show that
  the probed path is G1's path and that the counters did not change the physics.

Command (WSL, repo root): `~/.venvs/rubiknetic/bin/python experiments/D20_g1_magnet_check/g1_magnet_probe.py`.

## Result (`FACT`; `output_2026-11-28.txt`)
| Trial | Simulation steps | Magnet-force evaluations | Steps without magnet force | Differences vs rehearsal record |
|---|---|---|---|---|
| E1-2 U turn | 5,179 | 5,180 | **0** | 0 |
| E1-4 6-move sequence | 103,120 | 103,121 | **0** | 0 |
| E1-1 60 s rest | 142,000 | 142,002 | **0** | 0 |

**The magnet force was evaluated at every simulation step of all three G1 trial kinds.** The records are identical to
the committed rehearsal records. The extra evaluations (1–2 per trial) are setup `mj_forward` calls.

## Reading
- `INFERENCE`: G1's scored battery ran the same code path on its scored seeds (the runner is frozen and unchanged
  since the G1 run). The P-130 defect, which is specific to the two-arm scene's second model build, does not apply
  to G1. This upgrades the claim in the G2 pre-registration §0.1a from code reading to a runtime check on three trial
  kinds.
- Limit: E1-3, E1-5 to E1-7 were not probed. They use the same rig class and runner; a full 204-trial re-run was not
  done.
