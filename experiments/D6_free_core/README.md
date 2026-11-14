# D6 — Free-core M2 (cube held by a gripper, not fixed to the world), UNSCORED, 2026-11-13

**Why:** P-09 approved the fixed core for E1 scoring, on condition that a free-core, contact-held rig is tested before
Phase 2. In Phase 2 one arm holds the cube while the other turns a face.

**Model:** M2 (`experiments/M2_switched_welds`, used unchanged), with the core given a free joint and 1.7 g mass
(ASSUMPTION, Paulus 2023 BOM).

**Setup** (before t = 0, diagnostic only): gravity is off for 0.3 s while the holder closes.

## Results (FACT)

| Run | Holder | Switch rule | Result |
|---|---|---|---|
| `run_free.py orig` | M1 rig pads on the **opposite face (one layer)** | M2 original (rig pads count as requests) | **Wrong layer.** Commanding U unlocked D: the cube rotated 89.8° inside the held D layer, and the observed move was D. The following R slipped 7.8 mm |
| `run_free.py refined` | same | Original plus a relative-rotation gate | Same failure (D unlocked) |
| `run_stab.py shear stab_hold=DE` | **Two-layer stabiliser** (D+E, 30 N pads) | **Shear-dominance (PROPOSAL)** | **5/5** U U′ U2 U′ U correct; error ≤ 0.30°; drift 0.00°; core slip ≤ 0.28 mm; no core rotation; switch ΔKE ≤ 1e-8 J; 466 steps/s |
| `run_stab.py orig stab_hold=DE` | Two-layer stabiliser | M2 original | 2/2 correct. The original rule ignores the stabiliser because it reads only rig pads |
| `run_stab.py shear stab_hold=D` | **One-layer** stabiliser | Shear-dominance | **Refused correctly** (ambiguous loads): U did not turn and no illegal state arose, but the cube slid 13 mm in the grip |

## Findings

1. **Holding one layer is physically ambiguous** (INFERENCE, consistent with the runs). With equal and opposite
   torques on the U and D layers, "turn U" and "turn D plus rotate the cube" satisfy the loads equally well. A rigid
   model cannot choose between them, and a real cube's outcome would depend on friction details.
2. **A two-layer grip makes the turn unambiguous.** The shear at the U boundary is then clearly the largest.
   **This is a Phase 2 grasp requirement:** the stabilising arm must span two layers.
3. **The shear-dominance rule (PROPOSAL)** picks the right layer whenever the loads are unambiguous and refuses
   otherwise, while still reading physical state only. For a face F, the shear is the torque about F's axis, in the
   core frame, that all gripper contacts apply to F's layer cubies; F requests only if its shear is at least 1.5×
   the next face's.
   * In the fixed-core rig it is equivalent to the original rule.
   * In Phase 2, where fingertip contacts on held layers must be counted, it is needed.
   * Adopting it for scoring requires amending the M2 pre-registration (section 1), with approval, before any scored
     trial.

## Limits

* U turns only with the two-layer stabiliser.
* The stabiliser is idealised: rigid pads on world-fixed slides.
* Regrasping between faces was not tested with the stabiliser.
* Refusal messages are noisy during grip transients. They are harmless, but they should be rate-limited.
