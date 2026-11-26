# G2 step 1: robot model source, licences and torque ratings (status, 2026-11-26)

**Status.** A research note, written by the main session at the start of G2 (P-95: "G2, starting with design"). It
re-verifies the findings of [`PHASE_2_ROBOT_MODEL_FINDINGS.md`](PHASE_2_ROBOT_MODEL_FINDINGS.md) (2026-11-13) and
the P2 prototype (`experiments/P2_robot_model/`, unscored), and proposes how to close O-12 and O-13. Access date:
2026-11-26.

## Already established (`FACT`, on record)
**Model source** (`third_party_cad/robot/SOURCES.md`; P-17):
- **Arm:** MuJoCo Menagerie `ufactory_xarm7`, BSD-3-Clause, "Copyright (c) 2018, UFACTORY Inc.".
- **Joint limits and 1305+ meshes:** `xArm-Developer/xarm_ros2` (`humble`), also BSD-3-Clause © UFACTORY.
- **Gripper G2:** its meshes come from xarm_ros2's `*_g2.dae` (BSD-3), converted to STL. Its kinematics are the
  original gripper's (xarm_ros2 switches only the mesh filenames for G2).
- **G2 STEP CAD:** no licence text. The user authorised its use for measurements only (2026-11-13). Derived files
  stay git-ignored and are not redistributed.

**Torque (O-13).**
- No per-joint torque table is published: not on the spec page, in Hardware Manual v2.7.1 or in Developer Manual
  v2.0.1.
- The only official figures are the URDF's peak/overload efforts. For 1305+ they are 179.44 / 179.44 / 92 / 92 /
  81.558 / 30.6 / 30.6 N·m, derived as Kt × 100 × overload factor.
- The user accepted these as the working limits (P-17).
- `INFERENCE` (on record): the smallest wrist value is more than 30× the cube-turning torque, so the arm is not the
  limiting factor.

**P2 prototype** (`experiments/P2_robot_model/README.md`; unscored):
- the model loads in both hardware revisions;
- it holds pose under gravity (sag 0.0009 rad with actuator gravity compensation);
- G2 stroke is 83.1 mm (spec 84 ± 1);
- the pad span matches the STEP to 0.01 mm.

**Known open detail.** The Menagerie inertials total 12.07 kg (arm plus gripper), against 14.3 kg for the arm in the
1305 manual. That mismatch is unresolved. The 1305+ revision is the prototype's default; the user's hardware revision
is pending (P-17).

## Re-verified today (`FACT`)
- **xarm_ros2 `humble`:** no commit since 2026-10-20 (GitHub API, `commits?since=2026-10-21`: none). The effort values
  and G2 meshes are as recorded.
- **Menagerie `ufactory_xarm7`:** no commit since 2026-07-04 (GitHub API, path-filtered: none).
- **Torque ratings:** a web search for per-joint rated torque (2026-11-26) found none. Spec listings give only
  payload 3.5 kg, ±0.1 mm repeatability and 180°/s; one "rated torque 63 N" belongs to the linear-track option, not
  the arm.

## Proposals (need the user's approval)
1. **Close O-12.**
   - Model source: Menagerie arm + xarm_ros2 limits, meshes and G2 meshes, all BSD-3 © UFACTORY, with attribution
     kept.
   - G2 STEP: measurement-only, git-ignored, user-authorised. Not redistributed unless UFACTORY gives a licence.
2. **Close O-13** as "no per-joint rating published". Use the URDF peak values as limits (P-17), and record the
   continuous rating as unknown and non-limiting for cube turning.
3. **Hardware revision:** keep **1305+** as the model default unless the user's arms are pre-1305. If arms are
   bought later, check the serial or model number and switch if needed (both revisions are built).

## Sources
| Source | URL |
|---|---|
| MuJoCo Menagerie `ufactory_xarm7` | https://github.com/google-deepmind/mujoco_menagerie/tree/main/ufactory_xarm7 |
| xarm_ros2 (`humble`) | https://github.com/xArm-Developer/xarm_ros2 |
| UFACTORY downloads (G2 STEP) | https://www.ufactory.cc/download/ |
| Spec listing used in the torque search | https://qviro.com/product/xarm-5-lite-2-2/specifications |
| Weston Robot xArm guide | https://westonrobot.github.io/docs-legacy/robot_user_guide/ufactory/xarm.html |
