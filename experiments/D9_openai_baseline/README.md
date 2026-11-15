# D9 — OpenAI's simulated cube through our stage-1 tests (UNSCORED diagnostic)

**Question (user, 2026-11-14):**
- Is our cube better than the one OpenAI used?
- Could we just use theirs?

**Approach:** run OpenAI's released cube model through the same D8-1b stage-1 battery as our cubes, with the same
seeds, tests, oracle, edit audit and rig. The rules were written in [`PROTOCOL.md`](PROTOCOL.md) before any battery
result.

## Source
- OpenAI `robogym` (MIT license), commit `9ff1111fd557b1a01911d7d8c9d59a453071c96e`: `rubik_perpendicular.xml` and
  `roundcube.msh`.
- The files are copied unchanged into `robogym/`, with the licence; checksums and credit are in
  [`robogym/SOURCE.md`](robogym/SOURCE.md).
- This is the model released with the paper (S01/S02 in the source register). The variant used for the paper's
  results is not known (S02 note).

## Method
- **Adapter** (`openai_cube.py`; built by a subagent under P-20 and checked by the main session). It:
  - keeps their physics unchanged (0 mismatches over 86 joints and 27 geoms);
  - fixes their core to the world, as ours is;
  - maps names so that our unmodified harness reads and turns it;
  - rebuilds our gripper rig at their 19.05 mm pitch.
- **Variants:**
  - A uses our solver settings (0.5 ms, implicitfast).
  - B uses robogym's (8 ms, Euler; found in their shadowhand `assets.xml`). It was smoke-tested only: pieces drifted
    3.2° in 0.5 s at rest, possibly a rig artefact at 8 ms. The B battery was not run.
- **Run:** `run_stage1.py A` → `results/stage1/A/`; summary via `analyze_stage1.py ../../D9_openai_baseline/results/stage1`.

## Results, variant A (`FACT`, 2026-11-14)
Compared with our B1 cube without magnets, revision-2 harness, same seeds (`../D8_alignment/results/stage1_r2/B1_none`):

| Test | OpenAI cube | B1, no magnets |
|---|---|---|
| Sequences, moves matching the oracle | **63/140**: 6move, halves and sexy6_a pass; sexy6_b fails at move 12, scr20inv_a at move 12, scr20inv_b at move 6 | **103/140**: 5 of 6 pass; scr20inv_b jams at move 4 (a 60° jam) |
| Failure mode | The turn stops 12–14° short, penetration 7–9 mm, the state can't be read | Jam |
| Worst-piece misalignment, short sequences | 1.6° → 2.8–3.0° at the end (peak 4.5°) | 1.6–2.3° at the end (peak 3.8°) |
| Penetration on successful moves | 2.5–2.9 mm (max 5.1 mm on sexy6_a) | 0.29–0.35 mm |
| T1 snap-back | none (residual up to 5.2°) | none (residual up to 5.9°) |
| T2 forgiveness, ±2…±12° | **completes at every offset** | completes to ±10°; blocked at +12° (never illegal) |
| T5 opposed torque U+R, 1 and 2 N·m | **fail**: U 73–79° and R 34–39° both turn; radial change 10–12 mm (harness metric) | pass: U about 12°, R 4–6°, radial change 0.00 mm |
| T5 corner twist ±(1,1,1) | **numerical failure** (`mjWARN_BADQACC` at 2.1 s and 3.4 s) | categorical pass: 38–40° twist at 5 N·m, about 1 mm penetration |
| Edit-audit violations | 0 | 0 |
| Median steps/s (load average about 5) | 572 | 981 |

Gimbal lock (smoke test, `FACT`):
- After one quarter turn about y, 8 pieces' three-hinge chains have conditioning 0.003–0.02 (1 is healthy).
- Two pieces were near-singular after R U R' U'.
- The battery did not log conditioning, so its role in the sequence failures is **not established**.

## Interpretation (`INFERENCE`)
- **Used as a cube turned by a robot rig, OpenAI's released model is weaker than our B1 even without magnets.**
  - Its soft default contacts (2.5–2.9 mm penetration on normal moves) let pieces sink in and slide past each other.
  - Long sequences fail.
  - Opposed torques turn two perpendicular layers at once.
  - Corner twist blows up numerically.
- **The comparison is outside its design.** It was built for a free-floating cube in a dexterous hand, at an 8 ms
  step, with heavily randomised physics, and with a policy that realigned faces before turning. These results say
  it doesn't fit **our** task; they don't say it was a poor model for theirs.
- **It forgives better.** It completes perpendicular turns at every misalignment up to ±12°, which fits its rounded,
  soft pieces.
- **Answer to "could we just use theirs?": no.** Our contact-cube line (M1/B1) already improves on it for this
  task, and the gimbal-lock structure is a known liability for long sequences.

## Limits
- One seed per test, diagnostic only.
- Variant B was not run.
- The gimbal-lock contribution isn't separated from contact softness.
- The penetration metric is the minimum over all contacts, not split by pad versus piece contacts.
- The core is fixed (their setting has a free cube).
- Throughput was measured on a non-idle machine.
