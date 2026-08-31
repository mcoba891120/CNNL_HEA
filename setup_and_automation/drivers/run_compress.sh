#!/bin/bash

USER_DIR=$(pwd)
SIMULATION_MODE="compress"
ALLOY="NiCoTiZrHf"
TEMPERATURE="300"
VAR_NUM=7
NUM_GPU=0

for ORIENTATION in 100 110 111; do
    if [ "$ORIENTATION" -eq 100 ]; then
        X=20
        Y=10
        Z=10
        TOTAL_ATOM=$((X*Y*Z*2))
    elif [ "$ORIENTATION" -eq 110 ]; then
        X=15
        Y=7
        Z=10
        TOTAL_ATOM=$((X*Y*Z*4))
    elif [ "$ORIENTATION" -eq 111 ]; then
        X=12
        Y=7
        Z=4
        TOTAL_ATOM=$((X*Y*Z*12))
    else
        echo "Invalid orientation"
        exit 1
    fi

    # 構建 session name
    SESSION_NAME="v4_trial${VAR_NUM}_${TOTAL_ATOM}_${TEMPERATURE}k"

    # 執行 build_and_submit_simulation.sh 腳本
    ./build_and_submit_simulation.sh <<EOF
$SIMULATION_MODE
$ALLOY
$ORIENTATION
$SESSION_NAME
$X $Y $Z
$VAR_NUM
100000
$TEMPERATURE
$NUM_GPU
EOF

    # NUM_GPU 加 1
    NUM_GPU=$((NUM_GPU + 1))

done

exit 0
