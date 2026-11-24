# D15 — rounded piece edges (P-79)

**Approval.** The user approved this on 2026-11-24 ("fully approved"; DECISION_LOG P-79). The plan is
`../D14_noslip_rest_rehearsal/proposals/ROUNDED_EDGES_PROPOSAL_DRAFT.md`.

| Step | Status |
|---|---|
| R0 | done (below) |
| R1 | screen; fixed in its own protocol before it runs |
| R2 | needs a separate approval |

## R0 — implementation and static checks (`FACT`; all checks done 2026-11-24)

**Code.**
- `src/rubiknetic/cube_physics/m1_model.py` adds:
  - `M1Params.edge_profile` (`"chamfer"` default, or `"rounded"`) and `edge_radius`;
  - `_rounded_box_vertices` and `piece_vertices`;
  - `params_record`.
- The record writers in `scored.py`, `scored_m2.py` and `trials.py` use `params_record`. It leaves the edge fields out
  while they hold their defaults, so chamfer records are unchanged.
- The rounded geometry is the one the P-78 diagnostic tested (asserted by a test).

**Checks.**

| Check | Where | Result |
|---|---|---|
| Default (chamfer) model XML is byte-identical to before the change, for three parameter sets | `tests/test_edge_profile.py` (sha256 recorded at `07054f1`) | pass |
| Default record `params` keys are unchanged | same | pass |
| Rounded geometry: 104 vertices, extents = half-size, first facet at 15°, no cubie–cubie contact in the solved pose; bad settings raise | same | pass (13 tests) |
| One committed record per arm reproduces exactly: D14 Stage 2 E1-2 `U_s16100` at NoSlip 10, gates' comparison with the logging blocks stripped on both sides | `r0_repro.py` → `r0_repro.json` | L0, PG8, PG20: 0 differences, no proof errors |
| Composite checks V4 / V5 / V6 on the rounded geometry, NoSlip 10, R 1.4 and 2.5 mm, three arms | `r0_composite.py` → `r0_composite.json` | 6 / 6 pass. V4 rel. net force ≤ 4.1e-17; V5 energy drift 0.07–0.41 % (limit 1 %); V6 pass |
| Magnet fit: every piece magnet cylinder at least the 0.4 mm wall inside the piece solid | `r0_magnet_fit.py` → `r0_magnet_fit.json` | L0 48, PG8 56, PG20 68 piece magnets: all fit for the chamfer, R 1.4 and R 2.5. Minimum depth 0.40 mm in every case (the outer face), so rounding does not reach any magnet. Core magnets not reshaped, not checked. |
| Full test suite (`tests/` and D14's tests, WSL, MuJoCo 4.0.1) | — | all pass after one stale D14 test was updated (below) |

**The stale test.** `test_d14s3.py::test_assemble_counts_before_3b` asserted that every assembled trial passes. It was
written before Stage 3b had records. It failed only on the committed Stage 3b record `PG20 E1-4/scr20inv_s16400`, the
P-76 jam, and not because of R0. It now checks:
- that the Stage 1 + 2 trials (106 per arm) all pass;
- that Stage 3b holds exactly its 26 PG20 E1-4 records, with that one failure.
