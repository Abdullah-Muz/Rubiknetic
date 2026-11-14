# M2 — switched-weld cube (UNSCORED prototype, approved comparison model P-14)

The cubie geometry, joints and pad rig are M1's, unchanged (`radial_preload=0`: rigid radius). Equality welds are added:

* every non-centre cubie → core, plus cubie → each of the 6 centres (inactive);
* every centre → core.

That makes 146 welds: solref (1 ms, 1), solimp (0.99, 0.999, 0.1 mm).

**Switch rule** (`switching.py`). It uses only physical state: poses, hinge speed, and the torque the rig pads apply to
the cubies through contacts. It never uses the commanded move or the oracle.

* **Unlock F** when all of these hold:
  * no layer is unlocked;
  * every non-centre cubie is within 1.0° and 0.15 pitch of the lattice;
  * F's pads grip (more than 2 N);
  * the pad contact torque about F's axis exceeds 0.05 N·m.
* **Refuse** when:
  * two faces request at once;
  * the cube is misaligned;
  * another layer is still unlocked.

  Refusals are logged, and nothing moves.
* **Relock** when the centre hinge is within 0.5° of a multiple of 90°, every layer cubie is within 0.5°, the pad
  torque is below 0.02 N·m and the hinge speed is below 0.05 rad/s. Relocking also requires the layer to have moved
  more than 45°, or more than 1 s to have passed since the unlock.
* **Re-anchoring** at every switch sets the weld relpose to the CURRENT relative pose. The convention, verified in
  `probe_relpose.py` (residual 3e-17), is: `eq_data[3:6]` = body2 origin in the body1 frame, `[6:10]` = quaternion of
  body2 relative to body1. A switch therefore never snaps to an exact 90° and supplies no rotation energy.

**Audit exception.** `SwitchAuditedSim(AuditedSim)` additionally snapshots `mjModel.eq_data`. Only the registered
`SwitchManager` may change `eq_active` or `eq_data`, through `apply_switch`, and every change is logged. Any other
change to these, or to qpos, qvel, act, xfrc, qfrc or mocap, raises `EditAuditError`.

**Per-switch log:** t, face, number of members, pad torque, relative speed, pre-switch pose error (0 by
construction), post-switch pose error from `efc_pos`, ΔKE of the 26 cubies, impulse proxy (Σ|efc_force|·dt of the
new welds), penetration.

**Run:** `uv run python experiments/M2_switched_welds/run_m2.py <rest|seq|twist|forgive> [m1.turn_kp=20 m1.turn_kv=0.8] [degs=...]`.
Records are written to `results/`.
