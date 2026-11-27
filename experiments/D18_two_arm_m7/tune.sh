#!/bin/bash
# P-109 (3) arm B gain tuning study (UNSCORED; pilot seeds 29001-29002 only). Run from the repo root in WSL.
# 9 combinations K_P {1000,2000,4000} x D_P {30,60,120} at KI_P 8000, plus KI_P {4000,16000} at the nominal
# (2000, 60); each from 2 pilot seeds (cube start offset uniform +-1 mm per axis); U U' U2 U' U, F/T guard on.
P=~/.venvs/rubiknetic/bin/python
D=experiments/D18_two_arm_m7
mkdir -p $D/results/tune $D/logs/tune
jobs=()
for kp in 1000 2000 4000; do for dp in 30 60 120; do for s in 29001 29002; do jobs+=("$kp $dp 8000 $s"); done; done; done
for ki in 4000 16000; do for s in 29001 29002; do jobs+=("2000 60 $ki $s"); done; done
printf '%s\n' "${jobs[@]}" | xargs -P 8 -L 1 bash -c '$0 '$D'/two_arm.py --kp $1 --dp $2 --ki $3 --seed $4 --out '$D'/results/tune > '$D'/logs/tune/kp$1_dp$2_ki$3_s$4.txt 2>&1' $P
