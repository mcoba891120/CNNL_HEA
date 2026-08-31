#!/bin/bash
USER_DIR=$(pwd)
SIMULATION_MODE="relax"
ALLOY="NiCoTiZrHf"
ORIENTATION=110
CORE=25
X=17
Y=12
Z=12
VAR_NUM=3
# MC_TEMP=("mc300k" "mc1273k")
# EDGE_DIRS=("b100p110" "b110p110")
EDGE_DIRS=("b100p110")

# relax 模擬溫度列表（單位 K）
TEMPERATURES=(300 600 900)
TOTAL_ATOM=9792
RUN=100000

for e in "${EDGE_DIRS[@]}"; do
    for t in "${TEMPERATURES[@]}"; do
        SESSION_NAME="v3_trial${VAR_NUM}_${TOTAL_ATOM}_${t}k_${mct}_${e}"
        ./build_and_submit_simulation.sh <<EOF
$SIMULATION_MODE
$ALLOY
$ORIENTATION
$SESSION_NAME
$X $Y $Z
$VAR_NUM
100000
$t
$CORE
EOF
    done
done

exit 0
