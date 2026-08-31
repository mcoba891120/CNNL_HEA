#!/bin/bash
VERSION=7
TRIAL_START=1
TRIAL_END=5
RUN=100000
USER_DIR="/work/cnnltmp01/mcoba891120"
ALLOY="NiCoTiZrHf"

# Check if atomsk is available
command -v atomsk >/dev/null 2>&1 || { echo "Error: atomsk is required but not installed or not in PATH"; exit 1; }

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
    
    # Run LAMMPS with the specified GPU
    # if [ "$gpu_id" -lt 4 ]; then
    #     nohup mpirun -np 1 -cpu-set $gpu_id ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_a100 -k on g 1 -sf kk -pk kokkos newton on neigh half -log none -in "in.relax.$ALLOY.$(basename $folder_path)" > "STDOUT_$(basename $folder_path)" 2>&1 &
    # else
    #     nohup mpirun -np 1 -cpu-set $gpu_id ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -k on g 1 -sf kk -pk kokkos newton on neigh half -log none -in "in.relax.$ALLOY.$(basename $folder_path)" > "STDOUT_$(basename $folder_path)" 2>&1 &
    # fi
    nohup mpirun -np 1 -cpu-set $gpu_id ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -k on g 1 -sf kk -pk kokkos newton on neigh half -in "in.relax.$ALLOY.$(basename $folder_path)" > "STDOUT_$(basename $folder_path)" 2>&1 &
    cd - > /dev/null
    
    # Wait a moment to allow GPU to register the task
    sleep 5
}

# Function to check if a specific GPU is available
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

# Create task queue
declare -a task_queue
declare -a folder_paths

# Save current directory
SCRIPT_DIR=$(pwd)

# Create directories based on different temperatures, slip systems, and trials
echo "Creating task queue..."

# Loop through each trial number
for trial in $(seq $TRIAL_START $TRIAL_END); do
    # Create main trial directory
    main_trial_dir="v${VERSION}_trial${trial}"
    mkdir -p "$main_trial_dir"
    
    for t in "600"; do
        for slip_system in "b100p110" "b111p110"; do
            # Create subfolder name based on parameters
            subfolder_name="v${VERSION}_trial${trial}_9792_${t}k_${slip_system}"
            
            # Create directory path (subfolder inside main trial directory)
            folder_path="$SCRIPT_DIR/$main_trial_dir/$subfolder_name"
            mkdir -p "$folder_path"
            
            # Change to the subfolder
            cd "$folder_path"
            
            # Copy input file
            cp "relaxation/templates/in.relax.5quinary.var.NiCoTiZrHf" .
            
            # Determine which structure file to use
            if [ "$slip_system" = "b100p110" ]; then
                ORIGINAL_STRUCTURE="relaxation/NiCoTiZrHf_110/5quinary/NiCoTiZrHf_b100p110.data"
            else
                ORIGINAL_STRUCTURE="relaxation/NiCoTiZrHf_110/5quinary/NiCoTiZrHf_b111p110.data"
            fi
            
            # Copy structure file and duplicate along x-axis
            cp "$ORIGINAL_STRUCTURE" "./original_structure.data"
            echo "Duplicating structure file along x-axis for $subfolder_name..."
            atomsk "./original_structure.data" -duplicate 2 1 1 lmp temp.lmp && mv temp.lmp "./duplicated_structure.data"
            
            if [ ! -f "./duplicated_structure.data" ]; then
                echo "Error: Failed to create duplicated structure file for $subfolder_name"
                cd "$SCRIPT_DIR"
                continue
            fi
            
            # Use duplicated structure file as input
            STRUCTURE_PATH="$(pwd)/duplicated_structure.data"
            
            # Create input file with proper replacements
            sed -e "s|{{structure_path}}|${STRUCTURE_PATH}|g" \
                -e "s|{{version}}|$VERSION|g" \
                -e "s|{{var_num}}|$trial|g" \
                -e "s|{{session_name}}|$subfolder_name|g" \
                -e "s|{{run}}|$RUN|g" \
                -e "s|{{temperature}}|$t|g" \
                -e "s|{{user_dir}}|$USER_DIR|g" \
                "in.relax.5quinary.var.$ALLOY" > "in.relax.$ALLOY.$subfolder_name"
            
            # Return to script directory
            cd "$SCRIPT_DIR"
            
            # Add to task queue, recording full path
            task_queue+=("$subfolder_name")
            folder_paths+=("$folder_path")
        done
    done
done

# Process task queue
echo "Starting task processing..."
echo "Total tasks in queue: ${#task_queue[@]}"

# Maximum concurrent processes
MAX_CONCURRENT_PROCESSES=8  # Adjust based on system capacity

# Process tasks
task_index=0
while [ $task_index -lt ${#task_queue[@]} ]; do
    subfolder_name="${task_queue[$task_index]}"
    folder_path="${folder_paths[$task_index]}"
    
    # Check if maximum processes reached
    if ! check_max_processes $MAX_CONCURRENT_PROCESSES; then
        echo "Maximum concurrent processes reached. Waiting..."
        sleep 30  # Wait and retry
        continue
    fi
    
    # Try to find available GPU
    gpu_id=$(find_available_gpu)
    
    if [ -n "$gpu_id" ]; then
        echo "Found available GPU: $gpu_id"
        # Run task with correct path
        run_task "$folder_path" "$gpu_id"
        task_index=$((task_index + 1))
    else
        echo "No available GPU. Waiting..."
        sleep 30  # Wait and retry
    fi
    
    # Output progress
    echo "Processed $task_index / ${#task_queue[@]} tasks"
done

echo "All tasks have been processed!"