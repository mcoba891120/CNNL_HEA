#!/bin/bash

USER_DIR=$(pwd)
SIMULATION_MODE="relax"
ALLOY="NiCoTiZrHf"
ORIENTATION=100
VAR_NUM=8
NUM_GPU=0
# CORE=20
for TEMPERATURE in "300" "600" "900" ; do
    if [ "$ORIENTATION" -eq 100 ]; then
        X=20
        Y=20
        Z=20
        TOTAL_ATOM=$((X*Y*Z*2))
    elif [ "$ORIENTATION" -eq 110 ]; then
        X=15
        Y=14
        Z=20
        TOTAL_ATOM=$((X*Y*Z*4))
    elif [ "$ORIENTATION" -eq 111 ]; then
        X=12
        Y=14
        Z=8
        TOTAL_ATOM=$((X*Y*Z*12))
    else
        echo "Invalid orientation"
        exit 1
    fi

    # 構建 session name
    SESSION_NAME="var${VAR_NUM}_${TOTAL_ATOM}_${TEMPERATURE}k_stressMC"

    # 執行 build_and_submit_simulation.sh 腳本
    ./build_and_submit_simulation.sh <<EOF
$SIMULATION_MODE
$ALLOY
$ORIENTATION
$SESSION_NAME
$X $Y $Z
$VAR_NUM
10000
$TEMPERATURE
$NUM_GPU
EOF

    # NUM_GPU 加 1
    NUM_GPU=$((NUM_GPU + 1))

done

exit 0
