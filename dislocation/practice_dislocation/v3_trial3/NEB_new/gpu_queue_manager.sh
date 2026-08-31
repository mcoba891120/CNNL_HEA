#!/bin/bash

# GPU Queue Manager for NEB in.min tasks
# Detects node type and manages GPU resources accordingly

# Configuration
NEB_ROOT="dislocation/practice_dislocation/v3_trial3/NEB_new"
SLIP_SYSTEMS=("edge_b100_p100_NEB" "edge_b100_p110_NEB")
STRUCTURES=()  # If empty, scan all structure*; else only specified
RATIOS=("12.5pct" "16.7pct" "20pct" "25pct")
SCAN_INTERVAL=30
LOG_FILE="dislocation/practice_dislocation/v3_trial3/NEB_new/gpu_queue.log"

# NEB Mode Configuration
NEB_MODE=false
NEB_DIRECTORIES=()  # Directories to scan for neb_*.data files
NEB_COUNTER=0  # Counter for stdout_neb naming
FINAL_ENERGIES_FILE=""  # Will be set based on NEB directories

# GPU Configuration based on node
NODE_NAME=$(hostname)

# Check if we're actually on gpu05 by looking for A100 GPUs
if nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | grep -q "A100"; then
    echo "$(date): Detected A100 GPUs - Running on GPU05 - GPUs 0-3 A100, 4-7 V100" | tee -a "$LOG_FILE"
    A100_GPUS="0 1 2 3"
    V100_GPUS="4 5 6 7"
    MAX_A100_JOBS=4
    MAX_V100_JOBS=4
elif [[ "$NODE_NAME" == *"gpu04"* ]]; then
    echo "$(date): Running on GPU04 - All GPUs are V100" | tee -a "$LOG_FILE"
    A100_GPUS=""
    V100_GPUS="0 1 2 3 4 5 6 7"
    MAX_A100_JOBS=0
    MAX_V100_JOBS=8
elif [[ "$NODE_NAME" == *"gpu05"* ]]; then
    echo "$(date): Running on GPU05 - GPUs 0-3 A100, 4-7 V100" | tee -a "$LOG_FILE"
    A100_GPUS="0 1 2 3"
    V100_GPUS="4 5 6 7"
    MAX_A100_JOBS=4
    MAX_V100_JOBS=4
else
    echo "$(date): Unknown node $NODE_NAME, defaulting to V100 only" | tee -a "$LOG_FILE"
    A100_GPUS=""
    V100_GPUS="0 1 2 3 4 5 6 7"
    MAX_A100_JOBS=0
    MAX_V100_JOBS=8
fi

# Process tracking
declare -A RUNNING_JOBS  # GPU_ID -> "task_dir"
declare -A JOB_PIDS      # GPU_ID -> PID
declare -A JOB_STDOUT    # GPU_ID -> "stdout_file"

# Function to log messages
log_message() {
    echo "$(date): $1" | tee -a "$LOG_FILE"
}

# Silent logger (append to log only; no stdout)
log_silent() {
    echo "$(date): $1" >> "$LOG_FILE"
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--structures)
                if [[ -n "$2" ]]; then
                    IFS=',' read -ra STRUCTURES <<< "$2"
                    shift 2
                else
                    echo "Error: -t/--structures requires a value" >&2
                    exit 1
                fi
                ;;
            --neb)
                NEB_MODE=true
                shift
                ;;
            -d|--neb-dirs)
                if [[ -n "$2" ]]; then
                    IFS=',' read -ra NEB_DIRECTORIES <<< "$2"
                    shift 2
                else
                    echo "Error: -d/--neb-dirs requires a value" >&2
                    exit 1
                fi
                ;;
            -h|--help)
                echo "GPU Queue Manager"
                echo "Usage: $0 [-t structure1,structure2] [--neb] [-d dir1,dir2]"
                echo "  -t, --structures    Comma-separated list of structures to scan"
                echo "  --neb               Enable NEB mode for processing neb_*.data files"
                echo "  -d, --neb-dirs      Comma-separated list of directories to scan for neb_*.data files"
                exit 0
                ;;
            *)
                echo "Error: Unknown option '$1'" >&2
                echo "Use -h or --help for usage information"
                exit 1
                ;;
        esac
    done
}

# Function to detect completed gen_aligned_structure tasks
scan_for_completed_gen() {
    local completed_tasks=()
    local lr_count=0
    local next_count=0
    
    for slip_system in "${SLIP_SYSTEMS[@]}"; do
        slip_dir="$NEB_ROOT/$slip_system"
        if [[ ! -d "$slip_dir" ]]; then
            continue
        fi
        
        # Build structure dirs list
        local structure_dirs=()
        if [[ ${#STRUCTURES[@]} -gt 0 ]]; then
            for structure in "${STRUCTURES[@]}"; do
                local sd="$slip_dir/$structure"
                [[ -d "$sd" ]] && structure_dirs+=("$sd")
            done
        else
            for sd in "$slip_dir"/structure*; do
                [[ -d "$sd" ]] && structure_dirs+=("$sd")
            done
        fi
        
        for structure_dir in "${structure_dirs[@]}"; do
            # Check each ratio directory
            for ratio in "${RATIOS[@]}"; do
                ratio_dir="$structure_dir/$ratio"
                if [[ ! -d "$ratio_dir" ]]; then
                    continue
                fi
                
                # Find all Lx_Ry directories
                for lr_dir in "$ratio_dir"/L*_R*; do
                    if [[ ! -d "$lr_dir" ]]; then
                        continue
                    fi
                    ((lr_count++))
                    
                    # Check L*_R* directory itself
                    # Check if gen_aligned_structure completed successfully
                    if [[ -f "$lr_dir/STDOUT.gen" ]] && \
                       [[ -f "$lr_dir/HEA_init_edge3.data" ]] && \
                       [[ -s "$lr_dir/STDOUT.gen" ]] && \
                       [[ -s "$lr_dir/HEA_init_edge3.data" ]] && \
                       grep -q "Total Displacement" "$lr_dir/STDOUT.gen" 2>/dev/null; then
                        
                        # Check if in.min is not already running or completed
                        if [[ ! -f "$lr_dir/final.cfg" ]]; then
                            
                            # Check if this task is not already running
                            local already_running=false
                            for gpu_id in "${!RUNNING_JOBS[@]}"; do
                                if [[ "${RUNNING_JOBS[$gpu_id]}" == "$lr_dir" ]]; then
                                    already_running=true
                                    break
                                fi
                            done
                            
                            if [[ "$already_running" == false ]]; then
                                completed_tasks+=("$lr_dir")
                            fi
                        fi
                    fi
                    
                    # Check next_* subdirectories under L*_R*
                    for next_dir in "$lr_dir"/next_*; do
                        if [[ ! -d "$next_dir" ]]; then
                            continue
                        fi
                        ((next_count++))
                        
                        # For next_* directories, we only need to check if in.min exists
                        # and if the task is not already running or completed
                        if [[ -f "$next_dir/in.min" ]]; then
                            
                            # Check if in.min is not already running or completed
                            if [[ ! -f "$next_dir/final.cfg" ]]; then
                                
                                # Check if this task is not already running
                                local already_running=false
                                for gpu_id in "${!RUNNING_JOBS[@]}"; do
                                    if [[ "${RUNNING_JOBS[$gpu_id]}" == "$next_dir" ]]; then
                                        already_running=true
                                        break
                                    fi
                                done
                                
                                if [[ "$already_running" == false ]]; then
                                    completed_tasks+=("$next_dir")
                                fi
                            fi
                        fi
                    done
                done
            done
        done
    done
    
    # Return the completed tasks (don't log here to avoid polluting output)
    printf '%s\n' "${completed_tasks[@]}"
}

# Function to scan for NEB data files
scan_for_neb_files() {
    local completed_tasks=()
    
    # If no specific directories provided, scan NEB_ROOT
    local scan_dirs=()
    if [[ ${#NEB_DIRECTORIES[@]} -gt 0 ]]; then
        for dir in "${NEB_DIRECTORIES[@]}"; do
            if [[ -d "$dir" ]]; then
                scan_dirs+=("$dir")
            else
                log_silent "WARNING: NEB directory $dir does not exist"
            fi
        done
    else
        scan_dirs+=("$NEB_ROOT")
    fi
    
    for scan_dir in "${scan_dirs[@]}"; do
        # Find all neb_*.data files
        for neb_file in "$scan_dir"/neb_*.data; do
            if [[ ! -f "$neb_file" ]]; then
                continue
            fi
            
            local neb_dir=$(dirname "$neb_file")
            local neb_name=$(basename "$neb_file" .data)
            
            # Check if this NEB task is not already running or completed
            local stdout_file="$neb_dir/stdout_${neb_name}"
            
            # Skip if already completed (check if energy exists in CSV)
            if [[ -f "$FINAL_ENERGIES_FILE" ]] && grep -q "^${neb_name}," "$FINAL_ENERGIES_FILE" 2>/dev/null; then
                continue
            fi
            
            # Also check if there's a completed stdout file for this specific task
            local completed_stdout=""
            # Try to find a stdout file that might correspond to this neb_name
            for file in "$neb_dir"/stdout_${neb_name} "$neb_dir"/stdout_neb*; do
                if [[ -f "$file" ]]; then
                    if grep -q "Total wall time:" "$file" 2>/dev/null && grep -q "Energy initial, next-to-last, final" "$file" 2>/dev/null; then
                        # Check if this file hasn't been processed yet by looking at its energy
                        local file_energy=$(grep "Energy initial, next-to-last, final" "$file" -A 1 | tail -1 | grep -oE '[0-9.-]+$')
                        if [[ -n "$file_energy" ]] && ! grep -q ",$file_energy" "$FINAL_ENERGIES_FILE" 2>/dev/null; then
                            completed_stdout="$file"
                            break
                        fi
                    fi
                fi
            done
            
            # If we found a completed stdout file, extract energy and skip
            if [[ -n "$completed_stdout" ]]; then
                log_silent "Found completed task $neb_name, extracting energy from $completed_stdout"
                if extract_final_energy "$completed_stdout" "$neb_name" "$neb_dir"; then
                    log_silent "Extracted final energy for $neb_name from existing stdout"
                fi
                continue
            fi
            
            # Check if this task is not already running
            local already_running=false
            for gpu_id in "${!RUNNING_JOBS[@]}"; do
                if [[ "${RUNNING_JOBS[$gpu_id]}" == "$neb_dir:$neb_name" ]]; then
                    already_running=true
                    break
                fi
            done
            
            if [[ "$already_running" == false ]]; then
                completed_tasks+=("$neb_dir:$neb_name")
            fi
        done
    done
    
    # Return the completed tasks
    printf '%s\n' "${completed_tasks[@]}"
}

# Function to find available GPU
find_available_gpu() {
    # Check all available GPUs (A100 + V100)
    local all_gpus="$A100_GPUS $V100_GPUS"
    
    for gpu_id in $all_gpus; do
        if [[ -z "${RUNNING_JOBS[$gpu_id]}" ]]; then
            # Check if GPU is actually available
            if is_gpu_available "$gpu_id"; then
                echo "$gpu_id"
                return 0
            fi
        fi
    done
    
    echo ""
}

# Function to check if GPU is available
is_gpu_available() {
    local gpu_id="$1"
    
    # Check if GPU exists
    if ! nvidia-smi -i "$gpu_id" >/dev/null 2>&1; then
        return 1
    fi
    
    # Check memory usage
    local memory_info=$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits -i "$gpu_id")
    local memory_used=$(echo "$memory_info" | cut -d',' -f1 | tr -d ' ')
    local gpu_util=$(echo "$memory_info" | cut -d',' -f2 | tr -d ' ')
    
    # GPU is available if utilization < 10% and memory < 1000MB
    if [[ "$gpu_util" -lt 10 && "$memory_used" -lt 1000 ]]; then
        return 0
    else
        return 1
    fi
}

# Function to run in.min task
run_in_min_task() {
    local task_dir="$1"
    local gpu_id="$2"
    
    log_message "Starting in.min for $(basename "$task_dir") on GPU $gpu_id"
    
    cd "$task_dir" || return 1
    
    # Copy in.min if it doesn't exist (but not for next_* directories)
    if [[ ! -f "in.min" ]] && [[ ! "$task_dir" =~ next_ ]]; then
        cp "dislocation/practice_dislocation/v3_trial3/NEB_new/edge_b100_p100_NEB/new/change_ratio_12_5_300K/in.min" .
    fi
    
    # Copy SNAP files
    local snap_coeff="../../../../potentials/HEA_v3_trial3.snapcoeff"
    local snap_param="../../../../potentials/HEA_v3_trial3.snapparam"
    
    if [[ -f "$snap_coeff" ]]; then
        cp "$snap_coeff" .
        log_message "Copied SNAP coefficient file to $(basename "$task_dir")"
    else
        log_message "ERROR: SNAP coefficient file not found at $snap_coeff"
        return 1
    fi
    
    if [[ -f "$snap_param" ]]; then
        cp "$snap_param" .
        log_message "Copied SNAP parameter file to $(basename "$task_dir")"
    else
        log_message "ERROR: SNAP parameter file not found at $snap_param"
        return 1
    fi
    
    # Set GPU environment
    export CUDA_VISIBLE_DEVICES="$gpu_id"
    
    # Determine which LAMMPS executable to use
    local lammps_exe
    if [[ " $A100_GPUS " == *" $gpu_id "* ]]; then
        lammps_exe="/home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_a100"
    else
        lammps_exe="/home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100"
    fi
    
    # Run the task
    nohup mpirun -np 1 -cpu-set "$gpu_id" "$lammps_exe" \
        -k on g 1 -sf kk -pk kokkos newton on neigh half \
        -log none -in in.min > stdout 2>&1 &
    
    local pid=$!
    RUNNING_JOBS[$gpu_id]="$task_dir"
    JOB_PIDS[$gpu_id]=$pid
    
    log_message "Started in.min for $(basename "$task_dir") on GPU $gpu_id (PID: $pid)"
    
    cd - >/dev/null
}

# Function to run NEB task
run_neb_task() {
    local task_info="$1"
    local gpu_id="$2"
    
    # Parse task info (format: "directory:neb_name")
    local neb_dir="${task_info%:*}"
    local neb_name="${task_info#*:}"
    
    log_message "Starting NEB minimization for $neb_name on GPU $gpu_id"
    
    cd "$neb_dir" || return 1
    
    # Create NEB input file
    local neb_input="in.neb_${neb_name}"
    cat > "$neb_input" << EOF
atom_style      atomic
units           metal
boundary        p p p
read_data       ${neb_name}.data

mass     1 58.6934
mass     2 58.933195
mass     3 47.867
mass     4 91.224
mass     5 178.49

pair_style      snap
pair_coeff      * * ../../../../potentials/HEA_v3_trial3.snapcoeff ../../../../potentials/HEA_v3_trial3.snapparam Ni Co Ti Zr Hf
neighbor        1.0 bin
neigh_modify    every 5 delay 0 check yes
thermo		100

variable	upp_zhi equal bound(all,zmax)+1
variable	upp_zlo equal \${upp_zhi}-4.0
variable	bot_zlo equal bound(all,zmin)-1
variable	bot_zhi equal \${bot_zlo}+4.0
region		fix_upp block EDGE EDGE EDGE EDGE \${upp_zlo} \${upp_zhi} units box
region		fix_bot block EDGE EDGE EDGE EDGE \${bot_zlo} \${bot_zhi} units box
region		constrain union 2 fix_upp fix_bot
group		constrain region constrain
group	    	mobile subtract all constrain
fix		f constrain setforce NULL NULL 0

minimize	0.0 0.05 5000 1000
EOF
    
    # Set GPU environment
    export CUDA_VISIBLE_DEVICES="$gpu_id"
    
    # Determine which LAMMPS executable to use
    local lammps_exe
    if [[ " $A100_GPUS " == *" $gpu_id "* ]]; then
        lammps_exe="/home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_a100"
    else
        lammps_exe="/home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100"
    fi
    
    # Deterministic stdout naming per neb frame to avoid mismatches on restarts
    local stdout_file="stdout_${neb_name}"
    
    # Run the NEB task
    nohup mpirun -np 1 -cpu-set "$gpu_id" "$lammps_exe" \
        -k on g 1 -sf kk -pk kokkos newton on neigh half \
        -log none -in "$neb_input" > "$stdout_file" 2>&1 &
    
    local pid=$!
    RUNNING_JOBS[$gpu_id]="$task_info"
    JOB_PIDS[$gpu_id]=$pid
    JOB_STDOUT[$gpu_id]="$stdout_file"
    
    log_message "Started NEB minimization for $neb_name on GPU $gpu_id (PID: $pid, stdout: $stdout_file)"
    
    cd - >/dev/null
}

# Function to extract final energy from stdout
extract_final_energy() {
    local stdout_file="$1"
    local neb_name="$2"
    local neb_dir="$3"
    
    if [[ ! -f "$stdout_file" ]]; then
        return 1
    fi
    
    # Look for the energy line pattern - it spans multiple lines
    # First find the line with "Energy initial, next-to-last, final"
    local energy_line_num=$(grep -n "Energy initial, next-to-last, final" "$stdout_file" | tail -1 | cut -d: -f1)
    if [[ -n "$energy_line_num" ]]; then
        # Get the next line which contains the actual energy values
        local next_line_num=$((energy_line_num + 1))
        local energy_values=$(sed -n "${next_line_num}p" "$stdout_file")
        
        if [[ -n "$energy_values" ]]; then
            # Extract the final energy (last number in the line)
            local final_energy=$(echo "$energy_values" | grep -oE '[0-9.-]+$')
            if [[ -n "$final_energy" ]]; then
                # Only append to global energies file (no individual files)
                echo "$neb_name,$final_energy" >> "$FINAL_ENERGIES_FILE"
                
                # Sort the CSV file to maintain neb_1 to neb_9 order
                sort_csv_file
                
                log_message "Extracted final energy for $neb_name: $final_energy"
                return 0
            fi
        fi
    fi
    
    return 1
}

# Function to sort CSV file to maintain neb_1 to neb_9 order
sort_csv_file() {
    if [[ -f "$FINAL_ENERGIES_FILE" ]]; then
        # Create a temporary file with sorted data
        local temp_file=$(mktemp)
        
        # Keep the header
        head -1 "$FINAL_ENERGIES_FILE" > "$temp_file"
        
        # Sort the data lines by neb number
        tail -n +2 "$FINAL_ENERGIES_FILE" | sort -t',' -k1,1V >> "$temp_file"
        
        # Replace the original file
        mv "$temp_file" "$FINAL_ENERGIES_FILE"
    fi
}

# Function to monitor running jobs
monitor_running_jobs() {
    for gpu_id in "${!RUNNING_JOBS[@]}"; do
        local task_info="${RUNNING_JOBS[$gpu_id]}"
        local pid="${JOB_PIDS[$gpu_id]}"
        
        # Check if process is still running
        if ! kill -0 "$pid" 2>/dev/null; then
            log_message "Job on GPU $gpu_id (PID: $pid) has finished"
            
            # Check if this is a NEB task or regular in.min task
            if [[ "$task_info" == *":"* ]]; then
                # NEB task
                local neb_dir="${task_info%:*}"
                local neb_name="${task_info#*:}"
                
                # Get the stdout file for this specific NEB task
                local stdout_file="${JOB_STDOUT[$gpu_id]}"
                # Also try deterministic name
                if [[ -z "$stdout_file" ]]; then
                    local det_file="$neb_dir/stdout_${neb_name}"
                    [[ -f "$det_file" ]] && stdout_file="$det_file"
                fi
                
                # If stdout file is not set, try to find it
                if [[ -z "$stdout_file" ]]; then
                    # Try to find the specific stdout file for this task
                    # Look for stdout files that contain the completion marker
                    for file in "$neb_dir"/stdout_neb*; do
                        if [[ -f "$file" ]]; then
                            # Check if this stdout file contains the completion marker
                            if grep -q "Total wall time:" "$file" 2>/dev/null; then
                                # Check if this file has the right energy pattern
                                if grep -q "Energy initial, next-to-last, final" "$file" 2>/dev/null; then
                                    stdout_file="$file"
                                    break
                                fi
                            fi
                        fi
                    done
                fi
                
                if [[ -n "$stdout_file" ]]; then
                    log_message "SUCCESS: NEB task $neb_name completed successfully"
                    
                # Small delay to ensure file is flushed
                    sleep 0.5
                    
                    # Extract final energy
                    if extract_final_energy "$stdout_file" "$neb_name" "$neb_dir"; then
                        log_message "Final energy extracted for $neb_name"
                    else
                        # Attempt a second read after brief delay, then silence if still failing
                        sleep 0.5
                        if extract_final_energy "$stdout_file" "$neb_name" "$neb_dir"; then
                            log_message "Final energy extracted for $neb_name (retry)"
                        else
                            log_silent "Energy extraction still failing for $neb_name from $stdout_file"
                        fi
                    fi
                else
                    log_message "WARNING: NEB task $neb_name finished but no completion marker found"
                fi
            else
                # Regular in.min task
                local task_dir="$task_info"
                
                # Check if final.cfg was generated (success)
                if [[ -f "$task_dir/final.cfg" ]]; then
                    log_message "SUCCESS: $(basename "$task_dir") completed successfully"
                    
                    # Post-process final.cfg to final.txt
                    if [[ -f "$task_dir/final.cfg" ]]; then
                        local lines=($(wc -l < "$task_dir/final.cfg"))
                        if [[ $lines -gt 9 ]]; then
                            # Remove lines 1-3 and 5-9, keep line 4 and 10+
                            sed -e '1,3d' -e '5,9d' "$task_dir/final.cfg" > "$task_dir/final.txt"
                            log_message "Generated final.txt for $(basename "$task_dir")"
                        fi
                    fi
                else
                    log_message "WARNING: $(basename "$task_dir") finished but no final.cfg generated"
                fi
            fi
            
            # Clean up
            unset RUNNING_JOBS[$gpu_id]
            unset JOB_PIDS[$gpu_id]
            unset JOB_STDOUT[$gpu_id]
        fi
    done
}

# Function to count running jobs by type
count_running_jobs() {
    local a100_count=0
    local v100_count=0
    
    for gpu_id in "${!RUNNING_JOBS[@]}"; do
        if [[ " $A100_GPUS " == *" $gpu_id "* ]]; then
            ((a100_count++))
        else
            ((v100_count++))
        fi
    done
    
    echo "$a100_count $v100_count"
}

# Function to cleanup on exit
cleanup() {
    log_message "Shutting down GPU queue manager..."
    
    # Kill all running jobs
    for gpu_id in "${!JOB_PIDS[@]}"; do
        local pid="${JOB_PIDS[$gpu_id]}"
        if kill -0 "$pid" 2>/dev/null; then
            log_message "Terminating job on GPU $gpu_id (PID: $pid)"
            kill "$pid" 2>/dev/null
        fi
    done
    
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Main loop
main_loop() {
    log_message "Starting GPU queue manager on $NODE_NAME"
    log_message "A100 GPUs: $A100_GPUS (max jobs: $MAX_A100_JOBS)"
    log_message "V100 GPUs: $V100_GPUS (max jobs: $MAX_V100_JOBS)"
    
    if [[ "$NEB_MODE" == true ]]; then
        log_message "NEB MODE ENABLED"
        if [[ ${#NEB_DIRECTORIES[@]} -gt 0 ]]; then
            log_message "NEB directories: ${NEB_DIRECTORIES[*]}"
            # Set final energies file to the first specified directory
            FINAL_ENERGIES_FILE="${NEB_DIRECTORIES[0]}/final_energies.csv"
        else
            log_message "NEB directories: $NEB_ROOT (default)"
            # Set final energies file to NEB_ROOT
            FINAL_ENERGIES_FILE="$NEB_ROOT/final_energies.csv"
        fi
        # Initialize final energies file (create directory if it doesn't exist)
        local final_energies_dir=$(dirname "$FINAL_ENERGIES_FILE")
        if [[ ! -d "$final_energies_dir" ]]; then
            mkdir -p "$final_energies_dir"
            log_message "Created directory: $final_energies_dir"
        fi
        # Only create header if file doesn't exist
        if [[ ! -f "$FINAL_ENERGIES_FILE" ]]; then
            echo "neb_name,final_energy" > "$FINAL_ENERGIES_FILE"
        fi
        # Reset NEB counter for this run
        NEB_COUNTER=0
        log_message "Final energies will be saved to: $FINAL_ENERGIES_FILE"
    else
        if [[ ${#STRUCTURES[@]} -gt 0 ]]; then
            log_message "Selected structures: ${STRUCTURES[*]}"
        else
            log_message "Selected structures: ALL (structure*)"
        fi
    fi
    
    while true; do
        # Monitor existing jobs
        monitor_running_jobs
        
        # Count current running jobs
        read -r a100_running v100_running <<< "$(count_running_jobs)"
        
        if [[ "$NEB_MODE" == true ]]; then
            # NEB mode: scan for neb_*.data files (preserve lines safely)
            local neb_tasks=()
            while IFS= read -r line; do
                # accept only absolute paths of pattern ":neb_#" pairs
                [[ "$line" == /*:* ]] && neb_tasks+=("$line")
            done < <(scan_for_neb_files)
            
            log_message "Found ${#neb_tasks[@]} NEB tasks ready for execution"
            
            # Check if all NEB tasks are completed
            if [[ ${#neb_tasks[@]} -eq 0 ]] && [[ ${#RUNNING_JOBS[@]} -eq 0 ]]; then
                log_message "All NEB tasks completed! Shutting down..."
                cleanup
                exit 0
            fi
            
            # Process NEB tasks
            for task_info in "${neb_tasks[@]}"; do
                # Find available GPU
                local gpu_id=$(find_available_gpu)
                
                if [[ -n "$gpu_id" ]]; then
                    # Check if we haven't exceeded limits
                    read -r a100_running v100_running <<< "$(count_running_jobs)"
                    
                    local can_run=false
                    if [[ " $A100_GPUS " == *" $gpu_id "* ]]; then
                        if [[ $a100_running -lt $MAX_A100_JOBS ]]; then
                            can_run=true
                        fi
                    else
                        if [[ $v100_running -lt $MAX_V100_JOBS ]]; then
                            can_run=true
                        fi
                    fi
                    
                    if [[ "$can_run" == true ]]; then
                        run_neb_task "$task_info" "$gpu_id"
                        sleep 2  # Brief pause between job starts
                    fi
                else
                    log_message "No available GPUs for NEB task $task_info"
                    break
                fi
            done
            
            # Log NEB task list (silent to avoid polluting stdout)
            if [[ ${#neb_tasks[@]} -gt 0 ]]; then
                log_silent "NEB ready list has ${#neb_tasks[@]} items"
            fi
        else
            # Regular mode: scan for completed gen_aligned_structure tasks
            local completed_tasks=($(scan_for_completed_gen))
            
            # Log scanning statistics
            local lr_count=0
            local next_count=0
            for task_dir in "${completed_tasks[@]}"; do
                if [[ "$task_dir" == */next_* ]]; then
                    ((next_count++))
                else
                    ((lr_count++))
                fi
            done
            log_message "Scanned $lr_count L*_R* directories, $next_count next_* directories"
            
            # Separate L*_R* and next_* tasks for priority handling
            local lr_tasks=()
            local next_tasks=()
            
            for task_dir in "${completed_tasks[@]}"; do
                if [[ "$task_dir" == */next_* ]]; then
                    next_tasks+=("$task_dir")
                else
                    lr_tasks+=("$task_dir")
                fi
            done
            
            # Process L*_R* tasks first (higher priority)
            for task_dir in "${lr_tasks[@]}"; do
                # Find available GPU (no priority, just any available)
                local gpu_id=$(find_available_gpu)
                
                if [[ -n "$gpu_id" ]]; then
                    # Check if we haven't exceeded limits
                    read -r a100_running v100_running <<< "$(count_running_jobs)"
                    
                    local can_run=false
                    if [[ " $A100_GPUS " == *" $gpu_id "* ]]; then
                        if [[ $a100_running -lt $MAX_A100_JOBS ]]; then
                            can_run=true
                        fi
                    else
                        if [[ $v100_running -lt $MAX_V100_JOBS ]]; then
                            can_run=true
                        fi
                    fi
                    
                    if [[ "$can_run" == true ]]; then
                        run_in_min_task "$task_dir" "$gpu_id"
                        sleep 2  # Brief pause between job starts
                    fi
                else
                    log_message "No available GPUs for $(basename "$task_dir")"
                    break
                fi
            done
            
            # Process next_* tasks (lower priority)
            for task_dir in "${next_tasks[@]}"; do
                # Find available GPU (no priority, just any available)
                local gpu_id=$(find_available_gpu)
                
                if [[ -n "$gpu_id" ]]; then
                    # Check if we haven't exceeded limits
                    read -r a100_running v100_running <<< "$(count_running_jobs)"
                    
                    local can_run=false
                    if [[ " $A100_GPUS " == *" $gpu_id "* ]]; then
                        if [[ $a100_running -lt $MAX_A100_JOBS ]]; then
                            can_run=true
                        fi
                    else
                        if [[ $v100_running -lt $MAX_V100_JOBS ]]; then
                            can_run=true
                        fi
                    fi
                    
                    if [[ "$can_run" == true ]]; then
                        run_in_min_task "$task_dir" "$gpu_id"
                        sleep 2  # Brief pause between job starts
                    fi
                else
                    log_message "No available GPUs for $(basename "$task_dir")"
                    break
                fi
            done
            
            # Log task distribution
            if [[ ${#lr_tasks[@]} -gt 0 || ${#next_tasks[@]} -gt 0 ]]; then
                log_message "Found ${#lr_tasks[@]} L*_R* tasks, ${#next_tasks[@]} next_* tasks ready for execution"
                log_message "Ready lists:"
                if [[ ${#lr_tasks[@]} -gt 0 ]]; then
                    log_message "L*_R* ready list:"
                    for task_dir in "${lr_tasks[@]}"; do
                        log_message "  $task_dir"
                    done
                fi
                if [[ ${#next_tasks[@]} -gt 0 ]]; then
                    log_message "next_* ready list:"
                    for task_dir in "${next_tasks[@]}"; do
                        log_message "  $task_dir"
                    done
                fi
            fi
        fi
        
        # Show status
        read -r a100_running v100_running <<< "$(count_running_jobs)"
        log_message "Status: A100 jobs: $a100_running/$MAX_A100_JOBS, V100 jobs: $v100_running/$MAX_V100_JOBS"
        
        sleep "$SCAN_INTERVAL"
    done
}

# Run main loop
parse_arguments "$@"
main_loop
