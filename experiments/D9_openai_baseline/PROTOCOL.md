# D9 protocol: OpenAI robogym cube through Rubiknetic's stage-1 tests

Status: adapter built and smoke-tested only (2026-11-14). **No stage-1 battery result exists yet.** This protocol is
written before any battery result. It is a diagnostic comparison, not a G1 gate.

## Fairness rules

1. **Their physics is unchanged.** Geometry (19.0 mm `roundcube.msh` at 19.05 mm pitch), all 86 cubelet joints
   (driver hinges; rotx/roty/rotz hinges; radial `spring` slides with stiffness 500 N/m, range -1.0/+0.2 mm),
   joint defaults (damping, armature, frictionloss), geom density 521, condim 6, friction 0.2 0.0025 0.0005, and
   default solref/solimp are copied verbatim. `smoke.py load` compares every joint/dof/geom/body-mass/inertia value
   against the stripped source model; it must report zero mismatches before any battery run (it did: 86 joints,
   27 geoms, 0 mismatches).
2. **Core fixed (like for like).** robogym's `middle` body has 3 free slides + a ball joint (free cube in a hand).
   Rubiknetic's M1 rig v0 fixes the core to the world, so the adapter removes those 4 joints and renames `middle` to
   `core`. Results therefore describe OpenAI's cube *mechanism* on a fixed axle, not robogym's free-cube setting.
3. **Solver options, two variants.**
   - **A (ours):** M1Params options: timestep 0.5 ms, implicitfast, elliptic cone, impratio 10, Newton, 100
     iterations, tolerance 1e-10.
   - **B (robogym):** timestep 0.008 s, iterations 20, all other options MuJoCo defaults (Euler, pyramidal,
     Newton, impratio 1, tolerance 1e-8). FACT: `<option timestep="0.008" iterations="20" apirate="200">` in
     `robogym/assets/xmls/robot/shadowhand/assets.xml` lines 14-17 (commit 9ff1111), included by
     `robot/shadowhand/main.xml`, which `robogym/envs/dactyl/common/cube_env.py` merges into the cube env
     (`HAND_XML`, line 151). `n_substeps=10` (`cube_env.py` line 174; `full_perpendicular.py` line 60) is the control
     period (80 ms), not a physics change. INFERENCE: the cube env inherits this option element; no other option
     source was found in the files searched (`cube_env.py`, `full_perpendicular.py`, `mujoco_xml.py`, shadowhand
     `main.xml`/`chain.xml`, floor/light XMLs). ASSUMPTION: MuJoCo 4.0.1 defaults for the unset options equal those of
     the MuJoCo 2.0 / mujoco-py stack robogym used. robogym's training also randomised the timestep
     (`RandomizedTimestepWrapper`, `full_perpendicular.py` line 429); variant B uses the nominal value only.
     Note: in B the rig's pad/turner servos (tuned at 0.5 ms) run at 8 ms with Euler; rig instability there would be
     a rig artefact, and is to be reported as such, not as a cube property.
4. **Same seeds, same tests, same oracle.** The battery is `d8_1b_stage1.tests()` (seeds 5140-5145, 5160-5161,
   5170-5171, 5200+|d|, 5220+|d|) run through the unmodified functions `d8_1b_stage1.run_snap/run_seq` and
   `scored.run_forgiveness_trial/run_opposed_trial/run_corner_twist_trial`, with the same readout
   (`CubeReadout`), oracle (`cube_logic.observe`/`infer_move`), edit audit (`AuditedSim`) and monitor. No magnets.
   The adapter only patches, in-process, `scored.build_m1_xml`, `scored.apply_setup_misalignment` and
   `scored.params_for` (pitch 19.05 mm, gap 0.05 mm, plus the variant's solver options).
5. **Scored setup.** Same `draw_setup` (+-1 deg per face, grip force 10-20 N, turn speed 0.8-1.2 s/quarter). The
   per-face rotations are composed exactly as in `scored.apply_setup_misalignment` and realised through OpenAI's
   joints: the driver hinge for centres; for the 20 other pieces the rotx/roty/rotz angles are the exact intrinsic
   XYZ Euler decomposition of the target rotation. Written to qpos before t=0 only, logged, and verified against
   `mj_forward` body orientations (error < 1e-9).
6. **Preserve negative results;** report variant A and B side by side; never tune OpenAI parameters.

## Unavoidable differences (disclosed)

- Pitch 19.05 mm (theirs) vs 19.0 mm (M1); cubelet 19.0 mm rounded mesh (gap 0.05 mm) vs M1 chamfered box
  (18.8 mm, gap 0.2 mm, 1.4 mm bevel). The rig is rebuilt with pitch 19.05 mm / gap 0.05 mm, so pad heights and the
  idle-pad clearance (14 mm from the cube surface) and closing overshoot (6 mm) are the same relative to the cube.
- Pads: contype changed 2 -> 1 (rig side) so they collide with OpenAI's cubelets (contype=conaffinity=1) without
  editing OpenAI geoms. Pad-cubelet contact parameters are MuJoCo's mix of pad values (solref 0.001, friction 0.8,
  condim 4) and OpenAI's (default solref 0.02, solimp 0.9 0.95 0.001, condim 6): the pair gets condim 6, friction 0.8
  and an averaged solref/solimp, so the grip is not identical to M1's pad-cubie contact.
- Retention: OpenAI pieces have 3 serial hinges + radial spring (no preload); M1 has ball joints + 1 N preload
  slide. The 3-hinge chain becomes singular after quarter turns about y (gimbal lock); see smoke results.
- Mass: OpenAI density 521 kg/m3 on the mesh vs M1 3.4 g per cubie (not equalised: physics unchanged).
- The `center_sphere` geom (r = 10 mm) inside the core is kept; it does not reach the centre cubelets.
- Throughput is measured on a heavily loaded machine; re-measure on an idle one before quoting.
