# G2 verdict (scored): **PASS**

- scored trials: 128 (reported only: 10)
- turn trials: 100, failures 0, exact 95 % upper bound on the per-trial failure rate 0.030
- moves: 360
- G2-1 holds: 20/20 pass; max slip 0.1592546823986155 mm, max rotation 0.3411680316816005 deg
- G2-8 throughput (reported): real-time factor median 0.043387376866425 (138 trials)

| per-move maximum | value |
|---|---|
| turn_error_deg | 0.414 |
| nontarget_drift_deg | 0.307 |
| pen_cubie_mm | 0.144 |
| pen_pad_mm | 1.196 |
| ft_tau_z_max_Nm | 0.503 |
| max_tool_torque_on_layer_Nm | 0.513 |
| core_slip_mm | 0.260 |
| core_rot_deg | 1.237 |
| rollback_rot_deg | 0.092 |
| grasp_err_mm | 0.954 |
| armB_track_err_mm | 2.552 |
| core_slip_total_mm (trial) | 0.656 |
| core_rot_total_deg (trial) | 1.188 |
| residual_end_deg (trial) | 1.064 |
| residual_growth_deg (reported) (trial) | 0.788 |

| negative case | pass | outcome | reported only |
|---|---|---|---|
| collision_s30704 | True | robot contact detected | False |
| collision_s30705 | True | robot contact detected | False |
| jam_s30708 | True | guard stop at 43.6 deg | False |
| jam_s30709 | True | guard stop at 40.8 deg | False |
| offcentre_s30702 | True | clean | True |
| offcentre_s30703 | True | clean | True |
| open_midturn_s30706 | True | detected | False |
| open_midturn_s30707 | True | detected | False |
| two_layer_s30700 | True | detected | False |
| two_layer_s30701 | True | detected | False |

| G2-6 screen (reported only) | turns pass | reasons |
|---|---|---|
| grip10_s30603 | True | - |
| grip30_s30604 | True | - |
| grip50_stress_s30605 | True | - |
| kp_x0.5_s30600 | True | - |
| kp_x1.5_s30601 | True | - |
| mu0.5_s30602 | True | - |
| offset2mm_s30607 | False | cube 3.23 mm from nominal at t0 |
| rigid_pads_s30606 | True | - |
