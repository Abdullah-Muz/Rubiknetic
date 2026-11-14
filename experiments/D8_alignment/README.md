# D8 — Self-alignment for the cube model (UNSCORED diagnostics)

**Status:** D8-0 done (2026-11-14). P-18 approved: D8-1b. Its design proposal (magnet layout, strength, force law
and test plan) is in [`D8_1b_DESIGN_PROPOSAL.md`](D8_1b_DESIGN_PROPOSAL.md) and awaits user approval. No D8-1b model
has been built.
Nothing here is a scored G1 result. No model, switch rule, turner, setup, threshold or pre-registration was changed.

**Context.** M2 stalls on long sequences because each relock freezes the current misalignment, and the frozen
errors add up until a piece exceeds the 0.5° per-piece relock tolerance (D7). Real cubes, and OpenAI's contact
cube (S01: 1.425 mm bevels, turns attempted within ±0.1 rad ≈ 5.7°), self-align through geometry or magnets.
P-16 allows passive forces between specific pieces (such as magnet pairs). D8 asks where such forces would have to act.

## D8-0 — Can forces that act on whole layers remove M2's misalignment?

**Why it matters.** In M2 every piece is welded to the core or to its face centre. A force between pieces can only
rotate a whole unlocked layer about its axis; it cannot move one piece relative to the rest of its layer. Magnets on
M2 can only help if the error is mostly shared by all the pieces of a layer.

**Method** (`d8_0_decompose.py`):
1. Run the five D7 diagnostic sequences on unchanged M2: the scored `TrialM2` setup, the frozen turner, and no
   touch-ups. Seeds 2231, 2300, 2401, 4302 and 4401, never the scored range 3000–3999.
2. After setup and after every move, read each piece's 3-D residual rotation relative to its nearest lattice
   rotation.
3. Fit the six face-layer rotations that best remove it (small-angle least squares: 78 equations, 6 unknowns). The
   **residual** is the error that no combination of layer rotations can remove.

This is an **upper bound** on what layer-level forces can do, because it assumes all six layers are corrected
perfectly and at once. The run modes are:
- `approved`: the frozen SwitchRule.
- `loose`: diagnostic only. Per-piece relock and unlock tolerances are 3.0°, so sequences run longer and the error
  growth can be observed.

Snapshots taken after a stalled move are excluded, because a half-turned layer is not a resting error.

**Positive control** (`FACT`): the setup misalignment is applied per face, so it should be fully removable. At setup
the residual is ≤ 0.001° and 100 % of the error is removable in all five cases. The method recovers layer-level
error correctly.

### Results (`FACT`, `results/*.json`; source commit `1b0a5e4` plus the uncommitted Amendment 4 `src` changes, recorded as `src_dirty`)

| Case | Mode | Moves OK | Max error (last good) | Max residual (last good) | Removable share | First move with residual > 0.5° |
|---|---|---|---|---|---|---|
| halves_s2231 | approved | 3/6 | 0.55° | 0.28° | 84 % | – |
| halves_s2231 | loose | 6/6 | 0.76° | 0.24° | 91 % | – |
| scr20inv_s2401 | approved | 4/40 | 0.75° | 0.38° | 62 % | – |
| scr20inv_s2401 | loose | 14/40 | 1.78° | 0.72° | 81 % | move 6 |
| scr20inv_s4401 | approved | 23/40 | 0.59° | 0.47° | 46 % | – (peak 0.50°) |
| scr20inv_s4401 | loose | 16/40 | 1.31° | 0.61° | 78 % | move 16 |
| sexy6_s2300 | approved | 11/24 | 0.56° | 0.45° | 39 % | – |
| sexy6_s2300 | loose | 24/24 | 1.07° | 1.04° | 24 % | move 7 |
| sexy6_s4302 | approved | 6/24 | 0.59° | 0.47° | 38 % | move 4 |
| sexy6_s4302 | loose | 24/24 | 1.27° | 1.09° | 15 % | move 4 |

Other facts:
- Every run has zero edit-audit violations.
- In every `approved` run, the stall is a refused turn: "layer X still unlocked". The previous layer could not
  relock because a member piece exceeded 0.5°.
- The non-removable residual appears with the **first move** (0.08–0.42°) and keeps growing. In the 24-move `loose`
  runs it reaches about 1.0–1.2°, roughly 0.04° per move. By then only 15–24 % of the error could be removed by
  rotating layers.

### Interpretation

- `INFERENCE`: **layer-level forces cannot keep M2 inside its own tolerance on long sequences.** Even an ideal
  correction of all six layers leaves a piece-specific residual that passes 0.5° within 4–16 moves in four of the
  five `loose` runs. In the `approved` runs it is already 0.45–0.54° when the cube stalls. Magnets on M2 (option
  D8-1a) would delay the stall by a few moves at most.
- `INFERENCE` (mechanism, consistent with the positive control): each piece carries its error with it when its layer
  turns. A tilt picked up about one axis ends up about a different axis after the piece moves. Pieces that share a
  layer arrive with different histories, so their errors differ, and the welds keep each piece's own error. Weld
  compliance under pad load may add to this; D8-0 did not separate the two sources.
- `INFERENCE`: a real cube avoids the problem because each piece is held only by contact and can settle on its own.
  Correcting piece-specific error therefore needs forces that act **on each piece individually**, such as P-16
  magnet pairs or detents, in a model where pieces are not rigidly welded while they settle. That is option D8-1b: a
  bevelled contact cube in the style of S01/M1, with piece-to-piece magnets.
- Limits:
  - small-angle linear model (errors ≤ 2° here);
  - five sequences, one seed each;
  - an upper-bound argument, which rules out D8-1a rather than proving D8-1b will work;
  - the `loose` rule is not the pre-registered rule.

### Reproduce

```bash
# WSL, from the repo root; one case per process
~/.venvs/rubiknetic/bin/python experiments/D8_alignment/d8_0_decompose.py approved sexy6_s2300
~/.venvs/rubiknetic/bin/python experiments/D8_alignment/d8_0_decompose.py loose sexy6_s2300
```

Wall time is 44–343 s per case on 16 threads, with the ten runs in parallel.
