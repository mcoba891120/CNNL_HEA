#!/bin/bash

# 設定基本參數
USER_DIR=$(pwd)
ALLOY="NiCoTiZrHf"
TEMPERATURE="1273"
NUM_GPU=4
RUN=100000
CORE=64
VAR_NUM=3

# 定義所有配置
declare -A configs=(
    # Edge configurations
    # ["edge_100_100"]="edge 100 100 17 18 18"
    ["edge_100_110"]="edge 100 110 17 12 12"
    ["edge_110_110"]="edge 110 110 12 17 12"
    # ["edge_110_100"]="edge 110 100 12 12 17"
    # ["edge_111_110"]="edge 111 110 10 7 12"
    # # Screw configurations
    # ["screw_100_100"]="screw 100 100 17 18 18"
    ["screw_100_110"]="screw 100 110 12 17 12"
    ["screw_110_110"]="screw 110 110 17 12 12"
    # ["screw_110_100"]="screw 110 100 12 12 17"
    # ["screw_111_110"]="screw 111 110 7 10 12"
)

# 讀取simulation version
SIMULATION_VERSION="v3_trial3"

# 處理每個配置
for config_name in "${!configs[@]}"; do
    # 解析配置
    read -r dislocation_type b p x y z <<< "${configs[$config_name]}"
    
    echo "Processing: $config_name (${configs[$config_name]})"
    echo "Using GPU: $NUM_GPU"
    
    # 使用管道自動回答 "y"
    ./dislocation.sh <<EOF
$SIMULATION_VERSION
$ALLOY
$dislocation_type
$b
$p
$TEMPERATURE
$RUN
$VAR_NUM
$CORE
$x $y $z
$NUM_GPU
EOF
    
    echo "Completed: $config_name"
    echo "----------------------------------------"
    NUM_GPU=$((NUM_GPU + 1))
    
    # 等待一小段時間再執行下一個
    sleep 2
done

echo "All configurations completed"
exit 0
