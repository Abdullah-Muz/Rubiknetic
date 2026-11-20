# Robot and Gripper Model Sources: Findings (O-01, O-12, O-13)

**Date:** 2026-11-13 · **Scope:** documentation and model-source research, plus one MuJoCo load smoke test of an unmodified third-party model. **No Rubiknetic model, CAD, controller or training exists.** No phase gate is claimed.
**Tags:** `FACT` = read directly in the cited source on the access date · `INFERENCE` = derived from facts · `ASSUMPTION` · `PROPOSAL` · `VALIDATED_RESULT` = none in this report. The load test below is a **smoke test**, not validation.
**Supplements:** S19, S21 and S22 in `PHASE_0_SOURCE_REGISTER.md`. New source IDs use the prefix `RM-` so they do not collide with `S`-numbers.

---

## 1. Summary by open item

| Item | Status | One-line finding |
|---|---|---|
| **O-12** (G2 model source and licence) | **Narrowed** | **No MuJoCo (MJCF) model of the Gripper G2 was found.** The official `xarm_ros2` URDF (BSD-3-Clause) has supported `gripper_version:=G2` since 2026-04-23. It reuses the original-gripper kinematics and inertials and swaps in G2 meshes. Those meshes are `.dae`, which MuJoCo cannot load (STL/OBJ/MSH only), so they need conversion. The official G2 STEP CAD carries **no licence text**: licence unverified. |
| **O-01** (exact gripper and model) | **Narrowed** | Candidates: original xArm Gripper (Menagerie MJCF exists), **Gripper G2** (URDF + STEP only), BIO Gripper G2 (URDF + STEP; 20 N, 80 mm, a weak fit). The final choice remains the user's. |
| **O-13** (xArm7 joint torque ratings) | **Narrowed, not closed** | No torque table appears in the official spec page, Hardware Manual v2.7.1 or Developer Manual v2.0.1. The **official URDF config** gives *peak/overload* torques with a stated derivation: J1–J2 163.2, J3–J5 81.6, J6–J7 30.6 N·m (pre-1305 hardware); 179.44/179.44/92/92/81.56/30.6/30.6 N·m (≥1305). These are **not datasheet continuous ratings**. |

---

## 2. Model sources

### 2.1 MuJoCo Menagerie `ufactory_xarm7` (RM-01)

- `FACT`: files `xarm7.xml` (arm + original xArm Gripper), `xarm7_nohand.xml` (arm only), `hand.xml` (gripper only), `scene.xml`, and 16 STL meshes. Last path commit `71f066ad0be9` (2026-07-04); the sparse clone inspected was at repo HEAD `370c4396` (2026-11-10).
- `FACT`: **licence BSD-3-Clause, "Copyright (c) 2018, UFACTORY Inc."**. The README says it was derived from the `xarm_ros` URDF and requires MuJoCo ≥ 2.3.3.
- `FACT` (model content):
  - **Inertials:** present for every body. The arm masses equal the official `xarm7_type7_HT_BR2.yaml` inertial file (e.g. link1 2.382 kg, link7 0.17 kg).
  - **Actuators:** 7 `general` affine position servos (kp/kv 1500/150, 1000/100, 800/80) with `forcerange` ±50, ±50, ±30, ±30, ±30, ±20, ±20. There is 1 gripper actuator on a tendon (`ctrlrange` 0–255, `forcerange` ±50).
  - **Joints:** damping 10/10/5/5/5/2/2, `armature` 0.1 and `frictionloss` 1 on all joints. Ranges: J2 [−2.059, 2.0944], J4 [−0.19198, 3.927], J6 [−1.69297, 3.14159], other joints ±2π rad.
  - **Velocity limits:** none. MuJoCo has no joint velocity limit, so the controller must enforce one.
  - **Collision:** the arm link geoms use the **visual STL meshes as collision** (no separate collision set). Fingers collide only through 4 box pads (30 × 4 × 19 mm, friction 0.7/0.6). The four-bar linkage is closed with 2 `connect` equalities and 1 joint equality.
- `FACT`: Menagerie also has `ufactory_lite6` (BSD-3, © UFACTORY), which includes the Lite 6 gripper. That is a different arm and is not relevant to D-03.
- `INFERENCE`: the Menagerie `forcerange` values are **identical to the `xarm_ros2` URDF `effort` tags before 2026-10-20** (50/50/30/30/30/20/20; see RM-03 diff). They are inherited model placeholders, not manufacturer ratings.

### 2.2 MuJoCo 4.0.1 load smoke test (RM-01; scratch only, not in repo)

`FACT` (run 2026-11-13; WSL Ubuntu 24.04; project venv; `mujoco 4.0.1`; unmodified `ufactory_xarm7/scene.xml`):
- The model loads without error in 0.44 s. nbody 16, njnt 13, nq = nv = 13, nu 8, ngeom 21, nmesh 16, neq 3, ntendon 1. Timestep 0.002 s with `implicitfast`.
- Collision geoms: 13 mesh, 4 box, plus the floor and pedestal. Total model mass 12.07 kg.
- From the `home` keyframe, 2000 steps (4 s) ran at ≈54× real time on one CPU thread. Values stayed finite, with 0 contacts.
- **Max arm joint drift was 0.0155 rad (≈0.9°)** while holding position under gravity. Holding torques: J2 −13.6 N·m, J4 15.5 N·m.
- `INFERENCE`: the drift is P-servo sag (holding torque / kp), i.e. 15.45/1000 ≈ 0.015 rad on J4. Cube-scale precision will therefore need gravity compensation or a different low-level controller. This matches the spec's impedance-controller plan. One run on one machine: smoke test only.

### 2.3 Official UFACTORY ROS description packages (RM-02, RM-03)

- `FACT`: `xArm-Developer/xarm_ros` (ROS 1; default branch `master`) and `xArm-Developer/xarm_ros2` (default `humble`; also `jazzy`, `rolling` etc.) are both **BSD-3-Clause**, "Copyright (c) 2018, UFACTORY Inc.". Neither is archived; both were last pushed 2026-10-20. Inspected HEAD: `xarm_ros2@humble` `ac736c92b02d`.
- `FACT` (xarm_description, humble):
  - **URDF/xacro models:** xarm5/6/7, xarm7_mirror, uf850, lite6.
  - **Grippers:** `xarm_gripper` (parameter `gripper_version` `G1` | `G2`), `bio_gripper`, `uflite_gripper`, `vacuum_gripper`.
  - **Inertials:** per-SN inertial YAMLs (e.g. `xarm7_type7_HT_BR2`, `xarm7_type13_HT_BR2`) and per-SN kinematics calibration support.
- `FACT` (xArm7 URDF):
  - **Joint limits:** `velocity="3.14"` rad/s on all 7 joints. Default position limits J2 [−2.059, 2.0944], J4 [−0.19198, 3.927], J6 [−1.69297, π], others ±2π.
  - **Damping and friction:** `<dynamics damping="10" friction="1">` on J1. Other joints were not individually inspected.
  - **Meshes by hardware revision:**
    - Pre-1305 hardware uses its visual STL as collision.
    - `model_num ≥ 1305` (except 1380) uses separate `xarm7_1305/collision/*.obj` meshes.
- `FACT` (G2 in URDF):
  - **Added:** commit `74c98d4b92` (2026-04-23), "add dae model and support xArm Gripper G2 model". The same `*_g2.dae` meshes are also present in `xarm_ros` master (commit not compared).
  - **What changes for G2:** only the mesh filenames (`*_g2.dae`, used for both visual and collision).
  - **What stays the same as G1:** joint origins, `drive_joint` limit `0–0.85 rad, effort 50, velocity 2`, and inertials (base 0.54156 kg). The TCP stays at 0.172 m.
  - **Mesh format:** these are `.dae` files. Per the MuJoCo XML reference (RM-09), mesh files must be STL, OBJ or MSH, so **conversion is required**.
- `INFERENCE`: the G2 parallelogram link length in the official length formula (55.000 mm, RM-06) equals the URDF outer-knuckle→finger offset (√(35.465² + 42.039²) = 55.0 mm). This supports reusing the G1 linkage kinematics for G2. Masses (G2 820 g vs G1 802 g) and the finger mesh still differ.
- `FACT` (BIO gripper URDF): two prismatic fingers, limits ±0.04 m, `effort="2.0"`, `velocity="0.1"`. These are model values.

### 2.4 Official CAD downloads (RM-04)

- `FACT`: https://www.ufactory.cc/download/ lists:
  - xArm 7 (XS1305) STEP (12.1 MB)
  - xArm 7 "Articulated 3D Model" zip (7.9 MB)
  - Gripper G2 "3D With Fingers" and "3D Without Fingers" zips
  - BIO Gripper G2 3D zip
  - manuals
- `FACT`: the G2 zips each contain one SolidWorks-2019 AP214 STEP file ("Gripper AG1200 20250710" and "…without finger tips 20250721"). Each STEP has **a single merged PRODUCT**, not an assembly with separately named parts. Neither zip contains a licence file. The download page shows only "Copyright @ 2026 Ufactory All Rights Reserved"; its "Legal Notice" link has no reachable URL.
- **Licence status of UFACTORY CAD: `UNVERIFIED`.** Redistributing CAD-derived meshes in a public repo should wait for written permission or a clear licence from UFACTORY. Meshes from the BSD-3 `xarm_ros2` repo do not have this problem.

### 2.5 Other MuJoCo sources

- `FACT`: a GitHub search (2026-11-13) found only small personal xArm7-MuJoCo repos with 0–2 stars and mixed or absent licences. No G2 MJCF was found. **Not recommended** as sources.

---

## 3. xArm7 numbers

| Quantity | Value | Source / provenance |
|---|---|---|
| Payload | **3.5 kg** | `FACT` spec page RM-05 and Hardware Manual v2.7.1 §8.4 (RM-07) |
| Arm weight | 14.3 kg (1305 manual) | `FACT` RM-07. The Menagerie model totals 12.07 kg including the gripper: **mismatch**, inertial file vs hardware revision unresolved |
| Max joint speed | **180 °/s** (= 3.14 rad/s) | `FACT` RM-05, RM-07; URDF `velocity="3.14"` (RM-03) agrees |
| Joint accel / jerk (motion-command ranges) | 0–1145 °/s², 0–28647 °/s³ | `FACT` RM-07 motion-parameter table (text extraction partly garbled; check against the PDF before use) |
| Joint ranges (1305 hardware) | J2 −117…116°, J4 −6…225°, J6 −97…180°, others ±360° | `FACT` RM-05, RM-07 |
| Joint ranges (URDF / Menagerie / Developer Manual v2.0.1) | J2 −118…120°, J4 −11…225°, J6 −97…180° | `FACT` RM-01, RM-03, RM-08. **Wider than the 1305 spec on J2/J4** |
| Joint torque, pre-1305 | J1–J2 **163.2**, J3–J5 **81.6**, J6–J7 **30.6 N·m** | `FACT` `config/xarm7/joint_limits.yaml` (RM-03), comment "max torque = torque constant × 100 (gear ratio) × 2.55 (overload limit)". **URDF effort tag only; no datasheet. Peak/overload, not continuous** |
| Joint torque, ≥1305 | 179.44, 179.44, 92, 92, 81.558, 30.6, 30.6 N·m | `FACT` `joint_limits_1305.yaml` (RM-03), same derivation with Kt 0.955/0.46/0.15 and overload 1.879/2/1.773/2.04. Same caveat |
| Previous URDF efforts (before 2026-10-20) | 50, 50, 30, 30, 30, 20, 20 | `FACT` diff of commit `edf9418cd9` (RM-03). These equal the Menagerie `forcerange` |
| Torque readout | The Developer Manual offers a "joint torque … estimated based on current and theoretical model, for reference only" register (0x37) | `FACT` RM-08 |
| End flange | DIN ISO 9409-1-A50/63 (manual text shows M5/M6 ambiguously) | `FACT` RM-05 ("M6*6"), RM-07 (garbled) |

`INFERENCE`: even the smallest documented J7 value (Menagerie ±20 N·m) exceeds the 0.03–0.6 N·m cube-turning bracket by more than 30×. Wrist torque is therefore not the limiting factor. The `ASSUMPTION` in MECHANICAL_FEASIBILITY_ASSESSMENT §3 is supported, but only by vendor URDF data, not a datasheet.

---

## 4. Gripper numbers

| Gripper | Stroke | Force | Mass | Other | Source |
|---|---|---|---|---|---|
| xArm Gripper (original, G1) | 84 mm | max 30 N | 802 g | feedback: position | `FACT` RM-05 |
| **Gripper G2 (AG1200)** | **84 ± 1 mm** (command 0–840) | **10–50 N** (set as 1–100 %) | **820 g** (UM v2.7.1) / 800 g (HW manual) | Payload 5 kg; motor rated torque **0.22 N·m**, peak **0.5 N·m**, Kt 0.09 N·m/A; speed 15–225 mm/s; **feedback: position only**; fingers "Replaceable"; IP40 | `FACT` RM-06, RM-07 (mass discrepancy noted) |
| BIO Gripper G2 (AB1100) | 80 mm (working range 71–150 mm, or 4–83 mm with fingers reversed) | max 20 N | 790 g incl. adapter | fingers "can be freely customized" | `FACT` RM-10 |

**G2 geometry (D-04 interface), read from the drawings in UM v2.7.1 §6.2 (RM-06):**
- **Length formula:** L = 121.606 + √(55.000² − (0.5d − 8.997)²) mm, where d is the opening. L = 175.9 mm at d = 0, peaks at 176.6 mm near d ≈ 18 mm, and is 165.2 mm at d = 85 mm.
  - `INFERENCE`: the fingertip moves about 11 mm axially over the stroke. A fixed MJCF TCP (0.172 m) is only an approximation.
- **Open position:**
  - Finger region height 40 mm, measured along the gripper axis (direction of L).
  - Inner span 85 mm. Outer dimensions 99 / 113 / 170.8 mm.
  - `INFERENCE`: about 7 mm finger thickness per side.
- **Side view:** finger width 16 mm (27 / 32 mm housing).
- **Closed position:** 14 mm and 28 mm widths.
- **Flange:** Ø75 mm, Ø31.5 mm pilot, 8.3 mm thick, 2 × Ø6.6 mm holes with Ø12.6 × 90° countersink on 63 mm; mounted with 2 × M6 screws.
- **Fingertip fastening is not dimensioned in any official text or drawing found.** The side view shows two small holes on the finger (`INFERENCE`: fastener locations). `PROPOSAL`: measure the finger-mount face, hole spacing and thread from the "3D Without Fingers" STEP before designing fingertips.

---

## 5. Recommendation (`PROPOSAL`; requires user decision)

1. **Arm:** start from **Menagerie `ufactory_xarm7/xarm7_nohand.xml`** (BSD-3-Clause, © UFACTORY; loads in MuJoCo 4.0.1). Keep its licence and attribution. Document four deviations:
   - (a) Replace the placeholder `forcerange` values with documented values, either the URDF peak values or a conservative fraction of them, stating which.
   - (b) Decide whether to clip J2/J4 limits to the 1305 spec.
   - (c) Add controller-side velocity limits of 3.14 rad/s.
   - (d) Optionally use the BSD-3 `xarm7_1305` OBJ collision meshes if the hardware is 1305.
2. **Gripper:**
   - **Kinematics:** build a G2 MJCF from Menagerie `hand.xml`. Its four-bar is consistent with the 55 mm G2 link length.
   - **Meshes:** use the BSD-3 `*_g2.dae` meshes from `xarm_ros2`, converted to OBJ/STL.
   - **Fingers:** replace the fingers with the project's custom fingertips (D-04).
   - **Actuation:** map the actuator to the G2's 10–50 N range. This mapping needs calibration because the model actuates a tendon in joint space.
3. **Do not redistribute** STEP-derived geometry until the UFACTORY CAD licence is confirmed.

**Decisions for the user:**
- (i) Confirm G2 as the O-01 gripper.
- (ii) Which xArm7 hardware revision to model (1305 or earlier). This changes joint limits, torque table and collision meshes.
- (iii) Accept vendor URDF peak torques as the O-13 working values, or request a datasheet from UFACTORY.
- (iv) Whether to contact UFACTORY about the CAD licence.

---

## 6. Sources (accessed 2026-11-13)

| ID | Source | URL | Licence | What it establishes |
|---|---|---|---|---|
| RM-01 | MuJoCo Menagerie `ufactory_xarm7` (+ `ufactory_lite6`), path commit `71f066ad0be9`, repo HEAD `370c4396` | https://github.com/google-deepmind/mujoco_menagerie/tree/main/ufactory_xarm7 | BSD-3-Clause (© 2018 UFACTORY) | MJCF content, actuators, pads, inertials; source of the load test |
| RM-02 | UFACTORY `xarm_ros` (ROS 1) | https://github.com/xArm-Developer/xarm_ros | BSD-3-Clause | Same xArm7 URDF / joint_limits / G2 meshes |
| RM-03 | UFACTORY `xarm_ros2`, branch `humble` @ `ac736c92b02d`; commits `edf9418cd9` (effort update, 2026-10-20), `74c98d4b92` (G2, 2026-04-23) | https://github.com/xArm-Developer/xarm_ros2/tree/humble/xarm_description · https://github.com/xArm-Developer/xarm_ros2/commit/edf9418cd9 | BSD-3-Clause | URDF effort/velocity, joint_limits YAMLs, gripper variants, mesh formats |
| RM-04 | UFACTORY download centre | https://www.ufactory.cc/download/ | No licence stated ("All Rights Reserved" footer) | Availability of xArm7 / G2 / BIO CAD and manuals |
| RM-05 | UFACTORY xArm technical specifications | https://docs.xarm.ufactory.cc/8.technical_specifications.html | n/a (docs) | Payload, speed, joint ranges, flange, original gripper specs (= S21) |
| RM-06 | Gripper G2 User Manual v2.7.1 | https://www.ufactory.cc/upfiles/download/202611/7G03FG4AX9DZ.pdf | n/a | G2 specs incl. motor torque, drawings, flange, L(d) formula |
| RM-07 | xArm Hardware Manual (1305) v2.7.1 | https://www.ufactory.cc/upfiles/download/202606/UD72FEF224J3.pdf | n/a | 1305 joint ranges, motion limits, xArm7 3.5 kg / 14.3 kg, G2 summary (800 g); **no torque table** |
| RM-08 | xArm Developer Manual v2.0.1 | https://www.ufactory.cc/upfiles/download/202608/T7SCNVJFSZR0.pdf | n/a | Motion-parameter table (J2 −118…120°, J4 −11…225°), estimated-torque register; **no torque rating** |
| RM-09 | MuJoCo XML reference, `mesh` | https://mujoco.readthedocs.io/en/stable/XMLreference.html | n/a (docs; licence not checked) | Mesh files must be STL, OBJ or MSH |
| RM-10 | BIO Gripper G2 User Manual v2.8.0 | https://www.ufactory.cc/upfiles/download/202610/WJY8KDIK8B1F.pdf | n/a | BIO G2: 20 N, 80 mm, 790 g |

**Limitations:**
- PDF text was machine-extracted, so some tables are garbled. Drawing values were read from rendered pages.
- The STEP geometry was not measured.
- Only one MuJoCo load test was run, on the original-gripper model. No G2 MJCF was built or tested.
- The URDF torque values have not been confirmed by UFACTORY support.

## 7. Addendum 2026-11-19: O-13 re-check (status unchanged: narrowed, not closed)
A follow-up web search ran on 2026-11-19 under P-20. A subagent did the search, and the main session checked items 1
and 3 on their primary pages before recording them.
**No official UFACTORY document with a per-joint continuous (rated) or peak torque table was found, for either hardware
revision.**

| # | Source (accessed 2026-11-19) | What it establishes | Label |
|---|---|---|---|
| 1 | UFACTORY, *7. Production information*, https://docs.xarm.ufactory.cc/7.production_information.html, §7.13 | "The 1305 model of xArm series is model 4." The page gives no torque values. | `FACT`, official; checked by the main session |
| 2 | UFACTORY support article "xArm Series", `en/support_articles/developer/kinematic-and-dynamic-parameters/xArm_Series/README.md` in https://github.com/xArm-Developer/ufactory_doc_usermanual (branch `ufactory_doc_support_article`) | The serial number identifies the model. Character 1 gives the axis count (S = xArm 7). Character 11 gives the harmonic-drive type: A/E is model 4, L model 2, B model 1 or 3. A sibling file lists link masses and centres of mass for models 1–4. No torque, current or gear data | `FACT` as reported by the subagent; not re-checked |
| 3 | UFACTORY `ufactory_genesis` @ `c9793d4eb2c496bca961b62c014169a6e321b629` (MIT), `assets/configs/runtime/robots/xarm7_1305.yaml` | `force_lower_nm` / `force_upper_nm` / `effort_limits_nm` = ±[179.4445, 179.4445, 92, 92, 81.558, 30.6, 30.6] N·m; arm `kp` = [3000, 3000, 2000, 2000, 1000, 1000, 800]. Its changelog reportedly says the limits were set to match the default URDF | `FACT`, official; checked by the main session. **It corroborates RM-03's ≥1305 values but is not an independent source** |
| 4 | UFACTORY download centre (RM-04) | Still lists Hardware Manual v2.7.1 and Developer Manual v2.0.1. The v2.7.1 link now points to a different file (`/upfiles/download/202611/RE7G3GY52WQE.pdf`) from RM-07's | `FACT` as reported by the subagent. It reports no torque rating in either file |
| 5 | UFACTORY Forum, "Torque specifications", https://forum.ufactory.cc/t/torque-specifications/3531 | Seen **only as a search-engine summary**; the forum needs a login. The summary says: use continuous torque, and peak ≈ 2–2.5× continuous. It gives continuous values of about 42 N·m (J1/J2), 19 N·m (J3/J4) and 7 N·m (J5/J6) for the xArm 6, and 19 N·m (J3–J5) and 7 N·m (J6/J7) for xArm 5/6/7 | **Unverified.** Author, date, staff status and hardware revision are unconfirmed |

`INFERENCE`:
- **The forum figures, if accurate, do not fit the URDF peaks.** The URDF's pre-1305 peaks are 3.9–4.4× those
  continuous values, against the forum's stated 2–2.5×. So either the URDF "max effort" is a different quantity (for
  example an overload or current ceiling), or the forum figures apply to another revision or are conservative.
- **The URDF/Genesis values remain the only citable official numbers.** They are already the approved working limits
  (P-17). On either set, J7 (≥ 7 N·m) is far above the 0.03–0.6 N·m cube-turning bracket, so the margin conclusion in
  §3 holds.

**To close O-13:**
- the user reads forum thread 3531 with their own login; or
- the user asks UFACTORY support for continuous and peak torque per joint for model 4 (1305) and for earlier models.

P-17's record says UFACTORY will not be contacted ("its not needed"), so this second route is the user's choice.

## 8. Addendum 2026-11-19 (later the same day): forum thread 3531 read from a public archive copy
The user approved a Web-archive lookup (P-62 item 6). The Internet Archive holds a snapshot of the thread from
2024-02-28, taken when it was publicly readable. The main session read that snapshot directly.

**Source (RM-11).** UFACTORY Forum, "Torque specifications", thread 3531, archived at
https://web.archive.org/web/20240228182406/https://forum.ufactory.cc/t/torque-specifications/3531 (accessed
2026-11-19; SHA-256 of the raw archived HTML `cbae4a24…f8ebce`). Posts dated 13–19 February 2024.

`FACT` (what the thread says):
- A user asks for the peak and continuous torque of the xArm 6.
- Forum user "Minna" replies: "Please check the Cont. torque for xArm, the peak torque is 2-2.5 times." xArm 6:
  **J1/J2 42 N·m, J3/J4 19 N·m, J5/J6 7 N·m.**
- The user quotes an earlier reply by "Minna" in the thread "Maximum Torque Value Xarm 5/6/7": **J1/J2 42 N·m,
  J3/J4/J5 19 N·m, J6/J7 7 N·m**, and asks whether those are peak or continuous.
- "Minna" replies: "Confirmed, it's cont torque."

Caveats:
- The archived view does not mark "Minna" as staff. The poster answers a question addressed to UFACTORY, and the
  earlier search summary called the poster staff; that is not confirmed here.
- The thread does not name a hardware revision. It predates the 1305-specific URDF effort update (2026-10-20, RM-03).
- The earlier thread (2952) has archive copies from 2021-12-05 and 2022-05-20. A request to fetch them was refused by
  the session's permission check and was not attempted another way. Its content is known here only as quoted in
  thread 3531.

`INFERENCE`:
- **For the xArm 7, the forum's continuous torques are J1/J2 42, J3–J5 19 and J6/J7 7 N·m,** with a stated peak of
  2–2.5× (84–105, 38–47.5 and 14–17.5 N·m).
- **The official URDF "max effort" values are 1.6–2.2× above that stated peak** (pre-1305: 163.2 / 81.6 / 30.6 N·m)
  and 3.9–4.4× above the continuous values. The two sources therefore describe different quantities, or different
  hardware. The URDF comment calls its values "max torque = torque constant × 100 × overload limit".
- **Consequence for the model.** The P2 prototype uses the URDF values as actuator limits (P-17). If the forum
  values are right, those limits overstate what the arm can sustain by about 4×. For this project's task the margin
  is still large: the wrist joint's continuous 7 N·m is 12× the largest cube-turning torque in the bracket
  (0.6 N·m), and the payload (the 0.8 kg G2 gripper plus a cube of about 0.1 kg) is well inside the rated 3.5 kg. A Phase 2 check that commanded joint torques stay under the
  **continuous** values would make the result independent of which source is right (`PROPOSAL`).

**Status of O-13: the forum figures are now read from a primary (archived) page, but there is still no datasheet or
manual rating.** Whether that is enough to close O-13 is the user's decision.
