#!/bin/bash

# Function to find available GPUs
find_available_gpu() {
    # 获取当前正在使用的GPU列表
    used_gpus=$(nvidia-smi | awk '/Processes:/{flag=1} /\+--/{flag=0} flag && !/===/{print $2}' | grep -E '^[0-9]+$')
    
    # 获取系统中所有可用的GPU数量
    total_gpus=$(nvidia-smi --list-gpus | wc -l)
    
    # 初始化变量
    available_gpu=""
    min_memory=32768  # 假设每个GPU的内存为32GB

    
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