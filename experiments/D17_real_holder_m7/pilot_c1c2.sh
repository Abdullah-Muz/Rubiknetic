#!/bin/bash
# P-1 pilot (G2 pre-registration §7, P-105): C1 vs C2 (3 and 5 mm shoulders) x axial offset x lateral offset,
# sequence U U' U2 U' U, 20 N, soft pads. UNSCORED. Run from the repo root in WSL.
P=~/.venvs/rubiknetic/bin/python
L=experiments/D17_real_holder_m7/pilot_logs; mkdir -p $L
jobs=()
for t in "c1 3" "c2 3" "c2 5"; do set -- $t
  for ax in -2 0 2; do for lat in 0 1; do jobs+=("$1 $2 $ax $lat"); done; done; done
printf '%s\n' "${jobs[@]}" | xargs -P 9 -L 1 bash -c '$0 experiments/D17_real_holder_m7/turn.py --no-build --pilot --turner $1 --shoulder-mm $2 --ax-mm $3 --lat-mm $4 --tip-solref 0.01 > '$L'/$1_sh$2_ax$3_lat$4.txt 2>&1' $P
