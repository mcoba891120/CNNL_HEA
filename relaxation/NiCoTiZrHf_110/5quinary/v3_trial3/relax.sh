#!/bin/bash
VERSION=3
TRIAL=3
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
    nohup mpirun -np 1 -cpu-set $gpu_id ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -k on g 1 -sf kk -pk kokkos newton on neigh half -in "in.relax.$ALLOY.$(basename $folder_path)" > "STDOUT_$(basename $folder_path)" 2>&1 &
    
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

# Create task queue
declare -a task_queue
declare -a folder_paths

# Save current directory
SCRIPT_DIR=$(pwd)

# Create directories based on different temperatures and slip systems
echo "Creating task queue..."

for t in "300" "600" "900"; do
    for slip_system in "b100p110" "b111p110"; do
        # Create folder name based on parameters
        folder_name="v${VERSION}_trial${TRIAL}_9792_${t}k_${slip_system}"
        
        # Create directory and prepare files
        mkdir -p "$folder_name"
        cd "$folder_name"
        
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
        echo "Duplicating structure file along x-axis for $folder_name..."
        atomsk "./original_structure.data" -duplicate 2 1 1 lmp temp.lmp && mv temp.lmp "./duplicated_structure.data"
        
        if [ ! -f "./duplicated_structure.data" ]; then
            echo "Error: Failed to create duplicated structure file for $folder_name"
            cd "$SCRIPT_DIR"
            continue
        fi
        
        # Use duplicated structure file as input
        STRUCTURE_PATH="$(pwd)/duplicated_structure.data"
        
        # Create input file with proper replacements
        sed -e "s|{{structure_path}}|${STRUCTURE_PATH}|g" \
            -e "s|{{var_num}}|$TRIAL|g" \
            -e "s|{{session_name}}|$folder_name|g" \
            -e "s|{{run}}|$RUN|g" \
            -e "s|{{temperature}}|$t|g" \
            -e "s|{{user_dir}}|$USER_DIR|g" \
            "in.relax.5quinary.var.$ALLOY" > "in.relax.$ALLOY.$folder_name"
        
        # Return to script directory
        cd "$SCRIPT_DIR"
        
        # Add to task queue, recording full path
        task_queue+=("$folder_name")
        folder_paths+=("$SCRIPT_DIR/$folder_name")
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
    folder_name="${task_queue[$task_index]}"
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