#!/bin/bash

# Function to find available GPUs
find_available_gpu() {
    # Initialize variables
    available_gpu=""
    min_memory=32768  # Assuming max memory is 32GB
    check_duration=5  # 检查持续时间（秒）
    declare -A gpu_available_time  # 使用关联数组跟踪每个GPU的可用时间
    declare -A gpu_memory_used     # 记录每个GPU的内存使用
    
    # 初始时间标记
    start_time=$(date +%s)
    
    # 循环检查，最多检查10秒以避免无限循环
    while [ $(($(date +%s) - start_time)) -lt 10 ]; do
        # 获取所有GPU信息
        gpu_info=$(nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader,nounits)
        
        # 处理每个GPU的数据
        while IFS=, read -r index memory_used gpu_util; do
            # 移除空格
            index=$(echo "$index" | tr -d ' ')
            memory_used=$(echo "$memory_used" | tr -d ' ')
            gpu_util=$(echo "$gpu_util" | tr -d ' ')
            
            # 检查GPU是否符合条件
            if [ "$gpu_util" -lt 5 ] && [ "$memory_used" -lt 500 ]; then
                # GPU符合条件，增加计时器
                gpu_available_time[$index]=$((${gpu_available_time[$index]:-0} + 1))
                gpu_memory_used[$index]=$memory_used
                
                # 检查是否已经连续符合条件达到指定时间
                if [ ${gpu_available_time[$index]} -ge $check_duration ]; then
                    if [ "${gpu_memory_used[$index]}" -lt "$min_memory" ]; then
                        min_memory="${gpu_memory_used[$index]}"
                        available_gpu="$index"
                    fi
                fi
            else
                # 重置计时器
                gpu_available_time[$index]=0
            fi
        done <<< "$gpu_info"
        
        # 如果已找到可用GPU，跳出循环
        if [ -n "$available_gpu" ]; then
            break
        fi
        
        sleep 1
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
    nohup mpirun -np 1 -cpu-set $gpu_id ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -k on g 1 -sf kk -pk kokkos newton on neigh half -log none -in in.relax.NiCoTiZrHf.${folder_name} > STDOUT &
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
for mc_temperature in "" "mc300k" "mc1273k"; do
    for temperature in "300k" "600k" "900k"; do
        for slip_system in "b100p110" "b111p110"; do
            # 跳過空的MC溫度
            if [ "$mc_temperature" = "" ]; then
                echo "跳過: 無MC溫度"
                continue
            fi
            
            # 根據參數創建文件夾名
            folder_name="v3_trial3_9792_${temperature}_${mc_temperature}_${slip_system}"
            
            # 創建目錄並準備文件
            mkdir -p "$folder_name"
            cd "$folder_name"
            
            if [ "$mc_temperature" = "mc300k" ]; then
                cp "monte_carlo/MC_5quinary/NiCoTiZrHf_110_intraSubLattice/v3_trial3_9792_300k_${slip_system}/mc_folder/emin.data" .
            elif [ "$mc_temperature" = "mc1273k" ]; then
                cp "monte_carlo/MC_5quinary/NiCoTiZrHf_110_intraSubLattice/v3_trial3_9792_1273k_${slip_system}/mc_folder/emin.data" .
            fi
            
            # 複製輸入文件
            cp "relaxation/NiCoTiZrHf_110/5quinary/${folder_name}/in.relax.NiCoTiZrHf.${folder_name}" .
            
            # 準備數據文件
            atomsk emin.data -duplicate 2 1 1 lmp temp.lmp && mv temp.lmp emin_duplicated.data
            
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