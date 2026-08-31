#!/bin/bash
# Param
VERSION=7
# TRIAL=1
ALLOY="NiCoTiZrHf"
USER_DIR="/work/cnnltmp01/mcoba891120"
RUN=50000
TRIAL_START=1
TRIAL_END=2
GPU_EXCLUDE="6 7"

# Function to find available GPUs
find_available_gpu() {
    # Get list of GPUs currently in use
    used_gpus=$(nvidia-smi | awk '/Processes:/{flag=1} /\+--/{flag=0} flag && !/===/{print $2}' | grep -E '^[0-9]+$')
    
    # Get total number of available GPUs in the system
    total_gpus=$(nvidia-smi --list-gpus | wc -l)
    
    # Initialize variables
    available_gpu=""
    min_memory=99999999

    # Check each GPU to see if it's being used
    for gpu_id in $(seq 0 $((total_gpus - 1))); do
        # Check if this GPU is in the exclude list
        skip_gpu=false
        for exclude_id in $GPU_EXCLUDE; do
            if [ "$gpu_id" -eq "$exclude_id" ]; then
                skip_gpu=true
                break
            fi
        done
        
        # Skip this GPU if it's in the exclude list
        if [ "$skip_gpu" = true ]; then
            continue
        fi
        
        # Check if this GPU appears in the used list
        if ! echo "$used_gpus" | grep -q "^$gpu_id$"; then
            # Get memory usage for this GPU
            memory_info=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $gpu_id)
            memory_used=$(echo "$memory_info" | tr -d ' ')
            
            # If memory usage is less than current minimum, choose this GPU
            if [ "$memory_used" -lt "$min_memory" ]; then
                min_memory="$memory_used"
                available_gpu="$gpu_id"
            fi
        fi
    done
    
    echo "$available_gpu"
}

# Function to run a task on a specific GPU
run_task() {
    local folder_path=$1
    local gpu_id=$2
    
    echo "Running task for $(basename $folder_path) on GPU $gpu_id"
    cd "$folder_path"
    export CUDA_VISIBLE_DEVICES=$gpu_id
    # 如果gpu_id 為0到3則用lmp_kokkos_cuda_a100其餘用lmp_kokkos_cuda_v100
    if [ "$gpu_id" -lt 4 ]; then
        nohup mpirun -np 1 -cpu-set $gpu_id ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_a100 -k on g 1 -sf kk -pk kokkos newton on neigh half -log none -in in.compress.NiCoTiZrHf.$(basename $folder_path) > STDOUT &
    else
        nohup mpirun -np 1 -cpu-set $gpu_id ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -k on g 1 -sf kk -pk kokkos newton on neigh half -log none -in in.compress.NiCoTiZrHf.$(basename $folder_path) > STDOUT &
    fi
    # nohup mpirun -np 20 ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.relax.NiCoTiZrHf.${folder_name} > STDOUT &
    cd - > /dev/null
    
    # Wait a moment to allow GPU to register the task
    sleep 5
}

# Function to check if a specific GPU is available
is_gpu_available() {
    local gpu_id=$1
    
    # Check if GPU is available
    gpu_info=$(nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader,nounits | grep "^$gpu_id,")
    
    if [ -z "$gpu_info" ]; then
        return 1  # GPU not found
    fi
    
    memory_used=$(echo "$gpu_info" | cut -d',' -f2 | tr -d ' ')
    gpu_util=$(echo "$gpu_info" | cut -d',' -f3 | tr -d ' ')
    
    if [ "$gpu_util" -lt 5 ] && [ "$memory_used" -lt 500 ]; then
        return 0  # GPU is available
    else
        return 1  # GPU is busy
    fi
}

# Function to check if maximum number of processes are running
check_max_processes() {
    local max_processes=$1
    local current_processes=$(pgrep -c "lmp_kokkos_cuda_v100")
    
    if [ "$current_processes" -ge "$max_processes" ]; then
        return 1  # Maximum processes reached
    else
        return 0  # Below maximum processes
    fi
}

# 創建任務隊列
declare -a task_queue
declare -a folder_paths

# 主腳本
echo "正在創建任務隊列..."

# 使用絕對路徑保存當前工作目錄
SCRIPT_DIR=$(pwd)

# 根據不同溫度和滑移系統創建一系列文件夾，並放入相應的SS_curve文件
# mc前面加底線是為了避免沒有mc的時候出現連續兩個底線的情況
for TRIAL in $(seq $TRIAL_START $TRIAL_END); do
    mkdir -p "v${VERSION}_trial${TRIAL}"
    cd "v${VERSION}_trial${TRIAL}"
    version_trial_path=$(pwd)
    
    for temperature in "300" "600" "900"; do
        for slip_system in "b100p110" "b111p110"; do
            
            # 根據參數創建文件夾名
            folder_name="v${VERSION}_trial${TRIAL}_9792_${temperature}k_${slip_system}"
            
            # 創建目錄並準備文件
            mkdir -p "$folder_name"
            cd "$folder_name"
            
            cp "relaxation/NiCoTiZrHf_110/5quinary/v${VERSION}_trial${TRIAL}/${folder_name}/after_relax.data" .
            # 複製輸入文件
            cp "compression/templates/in.compress.5quinary.var.NiCoTiZrHf" .
            # atomsk after_relax.data -duplicate 2 1 1 lmp temp.lmp && mv temp.lmp after_relax_input.data
            sed -e "s|{{structure_path}}|./after_relax.data|g" \
            -e "s|{{var_num}}|$TRIAL|g" \
            -e "s|{{version}}|$VERSION|g" \
            -e "s|{{session_name}}|$folder_name|g" \
            -e "s|{{run}}|$RUN|g" \
            -e "s|{{temperature}}|$temperature|g" \
            -e "s|{{alloy}}|$ALLOY|g" \
            -e "s|{{user_dir}}|$USER_DIR|g" \
            "in.compress.5quinary.var.$ALLOY" > "in.compress.$ALLOY.$folder_name"
            
            cd "$version_trial_path"
            
            # 添加到任務隊列，記錄完整路徑
            task_queue+=("$folder_name")
            folder_paths+=("$version_trial_path/$folder_name")
        done
    done
    cd "$SCRIPT_DIR"
done

# 處理任務隊列
echo "開始處理任務..."
echo "隊列中總任務數: ${#task_queue[@]}"

# 最大並發進程數
MAX_CONCURRENT_PROCESSES=8  # 根據系統能力調整

# 處理任務
task_index=0
while [ $task_index -lt ${#task_queue[@]} ]; do
    folder_name="${task_queue[$task_index]}"
    folder_path="${folder_paths[$task_index]}"
    
    # 檢查是否超過最大進程數
    if ! check_max_processes $MAX_CONCURRENT_PROCESSES; then
        echo "已達到最大並發進程數。等待中..."
        sleep 30  # 等待並重試
        continue
    fi
    
    # 嘗試找到可用的GPU
    gpu_id=$(find_available_gpu)
    
    # if [ -n "$gpu_id" ] && ["$gpu_id" -eq ]; then
    #     echo "找到可用GPU: $gpu_id"
    #     # 使用正確的路徑運行任務
    #     run_task "$folder_path" "$gpu_id"
    #     task_index=$((task_index + 1))
    # else
    #     echo "沒有可用的GPU。等待中..."
    #     sleep 30  # 等待並重試
    # fi
    if [ -n "$gpu_id" ]; then
        echo "找到可用GPU: $gpu_id"
        run_task "$folder_path" "$gpu_id"
        task_index=$((task_index + 1))
    fi
    # 輸出進度
    echo "已處理 $task_index / ${#task_queue[@]} 個任務"
done

echo "所有任務已處理完成！"