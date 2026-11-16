import json, numpy as np
j = json.load(open("/mnt/c/Users/abdul/AppData/Local/Temp/claude/b6672f8dce1e00f4/3140f1d7-6e9e-4f5a-9e6c-c7e61a5f6350/scratchpad/diag/sexy6_s7312_12_gap0.1.json"))
pm = j["per_move"]; rows = j["rows"]
print(pm["move"], "t_pad", pm["t_pad_force_s"], "t_motion", pm["t_layer_motion_s"], "ok_causal", pm["ok_causal"])
tm = pm["t_layer_motion_s"]
for r in rows:
    if tm - 0.12 <= r["t"] <= pm["t_pad_force_s"] + 0.05:
        te = np.array(r["tl_err_deg"])
        print(f" t {r['t']:.4f} pad {r['pad_N']:6.3f}N  layer {r['layer_dps']:+7.2f} dps rot {r['layer_rot_deg']:+.4f}  layer magτ {r['layer_mag_Nm']:+.5f}  turn-layer piece err mean {te.mean():+.3f} [{te.min():+.3f},{te.max():+.3f}]")
