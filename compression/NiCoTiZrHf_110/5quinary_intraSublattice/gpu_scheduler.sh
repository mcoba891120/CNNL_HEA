#!/bin/bash

# Function to find available GPUs
find_available_gpu() {
    # 获取当前正在使用的GPU列表
    used_gpus=$(nvidia-smi | awk '/Processes:/{flag=1} /\+--/{flag=0} flag && !/===/{print $2}' | grep -E '^[0-9]+$')
    
    # 获取系统中所有可用的GPU数量
    total_gpus=$(nvidia-smi --list-gpus | wc -l)
    
    # 初始化变量
    available_gpu=""
    min_memory=99999999

    
    # 检查每个GPU是否被使用
    for gpu_id in $(seq 0 $((total_gpus - 1))); do
        # 检查此GPU是否出现在使用列表中
        if ! echo "$used_gpus" | grep -q "^$gpu_id$"; then
            # 获取此GPU的内存使用情况
            memory_info=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $gpu_id)
            memory_used=$(echo "$memory_info" | tr -d ' ')
            
            # 如果内存使用小于当前最小值，则选择此GPU
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
    local folder_name=$1
    local gpu_id=$2
    
    echo "Running task for $folder_name on GPU $gpu_id"
    cd "$folder_name"
    export CUDA_VISIBLE_DEVICES=$gpu_id
    nohup mpirun -np 1 -cpu-set $gpu_id ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -k on g 1 -sf kk -pk kokkos newton on neigh half -log none -in in.compress.NiCoTiZrHf.${folder_name} > STDOUT &
    # nohup mpirun -np 20 ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.relax.NiCoTiZrHf.${folder_name} > STDOUT &
    cd ../
    
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

# 主腳本
echo "正在創建任務隊列..."

# 根據不同溫度和滑移系統創建一系列文件夾，並放入相應的SS_curve文件
# mc前面加底線是為了避免沒有mc的時候出現連續兩個底線的情況
for mc_temperature in "" "_mc300k" "_mc1273k"; do
    for temperature in "300k" "600k" "900k"; do
        for slip_system in "b100p110" "b111p110"; do
            
            
            # 根據參數創建文件夾名
            folder_name="v3_trial3_9792_${temperature}${mc_temperature}_${slip_system}"
            
            # 創建目錄並準備文件
            mkdir -p "$folder_name"
            # 跳過空的MC溫度
            if [ "$mc_temperature" = "" ]; then
                cd "$folder_name"
                cp "compression/NiCoTiZrHf_110/5quinary/${folder_name}/SS_curve_v3_trial3_9792_${temperature}_${slip_system}.txt" .
                cd ../
                continue
            fi
            cd "$folder_name"
            
            if [ "$mc_temperature" = "_mc300k" ]; then
                cp "relaxation/NiCoTiZrHf_110/5quinary_intraSublattice/${folder_name}/after_relax.data" .
            elif [ "$mc_temperature" = "_mc1273k" ]; then
                cp "relaxation/NiCoTiZrHf_110/5quinary_intraSublattice/${folder_name}/after_relax.data" .
            fi
            
            # 複製輸入文件
            cp "compression/NiCoTiZrHf_110/5quinary/${folder_name}/in.compress.NiCoTiZrHf.${folder_name}" .
            
            cd ../
            
            # 添加到任務隊列
            task_queue+=("$folder_name")
        done
    done
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
    
    # 檢查是否超過最大進程數
    if ! check_max_processes $MAX_CONCURRENT_PROCESSES; then
        echo "已達到最大並發進程數。等待中..."
        sleep 30  # 等待並重試
        continue
    fi
    
    # 嘗試找到可用的GPU
    gpu_id=$(find_available_gpu)
    
    if [ -n "$gpu_id" ]; then
        echo "找到可用GPU: $gpu_id"
        run_task "$folder_name" "$gpu_id"
        task_index=$((task_index + 1))
    else
        echo "沒有可用的GPU。等待中..."
        sleep 30  # 等待並重試
    fi
    
    # 輸出進度
    echo "已處理 $task_index / ${#task_queue[@]} 個任務"
done

echo "所有任務已處理完成！"