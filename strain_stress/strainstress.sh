#!/bin/bash

USER_DIR=$(pwd)
SIMULATION_MODE="compress"
ALLOY="NiCoTiZrHf"
VAR_NUM=3
# NUM_GPU=1
CORE=30
for ORIENTATION in 110 111 ; do
    for TEMPERATURE in "300" "600" "900" ; do
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
        SESSION_NAME="var${VAR_NUM}_${TOTAL_ATOM}_${TEMPERATURE}k_stressMC"

        # 執行 build_and_submit_simulation.sh 腳本
        ../setup_and_automation/drivers/build_and_submit_simulation.sh <<EOF
$SIMULATION_MODE
$ALLOY
$ORIENTATION
$SESSION_NAME
$X $Y $Z
$VAR_NUM
10000
$TEMPERATURE
$CORE
EOF
done
    done

exit 0
