#!/bin/bash

# NEB Scheduler - Manages in.neb jobs with CPU core monitoring
# Monitors CPU usage and schedules NEB jobs within core limits

# Configuration
NEB_ROOT="dislocation/practice_dislocation/v3_trial3/NEB_new"
ALL_SLIP_SYSTEMS=("edge_b100_p100_NEB")
ALL_STRUCTURES=("structure1" "structure2")
RATIOS=("12.5pct" "16.7pct" "20pct" "25pct")

# Default to all slip systems and structures if not specified
SLIP_SYSTEMS=("${ALL_SLIP_SYSTEMS[@]}")
STRUCTURES=("${ALL_STRUCTURES[@]}")
SCAN_INTERVAL=60
LOG_FILE="dislocation/practice_dislocation/v3_trial3/NEB_new/neb_scheduler.log"
# Dynamically detect visible CPU cores (matches Open MPI slot visibility)
TOTAL_SYSTEM_CORES=$(nproc)
# Cap our usage to 256 cores maximum
MAX_OUR_CORES=512
NEB_CORES_PER_JOB=126
LOOP=9
CORE=$((${NEB_CORES_PER_JOB} / ${LOOP}))
LAMMPS_EXE="/home/jhenyu/lammps-stable_2Aug2023_update2/src/lmp_g++_openmpi"

# Process tracking
declare -A RUNNING_JOBS  # JOB_ID -> "task_dir"
declare -A JOB_PIDS      # JOB_ID -> PID
declare -A JOB_CORES     # JOB_ID -> core_count

# Function to show help
show_help() {
    echo "NEB Scheduler - Manages in.neb jobs with CPU core monitoring"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -s, --slip-systems SLIP1,SLIP2,...  Specify slip systems to run (comma-separated)"
    echo "  -t, --structures STRUCT1,STRUCT2,... Specify structures to run (comma-separated)"
    echo "  -h, --help                          Show this help message"
    echo ""
    echo "Available slip systems:"
    printf "  %s\n" "${ALL_SLIP_SYSTEMS[@]}"
    echo ""
    echo "Available structures:"
    printf "  %s\n" "${ALL_STRUCTURES[@]}"
    echo ""
    echo "Examples:"
    echo "  $0                                          # Run all slip systems and structures"
    echo "  $0 -s edge_b100_p100_NEB                   # Run only edge_b100_p100_NEB for all structures"
    echo "  $0 -t structure1,structure2                # Run all slip systems for structure1 and structure2"
    echo "  $0 -s edge_b100_p100_NEB -t structure1     # Run only edge_b100_p100_NEB for structure1"
    echo ""
}

# Function to parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--slip-systems)
                if [[ -n "$2" ]]; then
                    IFS=',' read -ra SLIP_SYSTEMS <<< "$2"
                    # Validate slip systems
                    for slip in "${SLIP_SYSTEMS[@]}"; do
                        if [[ ! " ${ALL_SLIP_SYSTEMS[*]} " =~ " $slip " ]]; then
                            echo "Error: Invalid slip system '$slip'"
                            echo "Available slip systems: ${ALL_SLIP_SYSTEMS[*]}"
                            exit 1
                        fi
                    done
                    shift 2
                else
                    echo "Error: -s/--slip-systems requires a value"
                    exit 1
                fi
                ;;
            -t|--structures)
                if [[ -n "$2" ]]; then
                    IFS=',' read -ra STRUCTURES <<< "$2"
                    # Validate structures
                    for struct in "${STRUCTURES[@]}"; do
                        if [[ ! " ${ALL_STRUCTURES[*]} " =~ " $struct " ]]; then
                            echo "Error: Invalid structure '$struct'"
                            echo "Available structures: ${ALL_STRUCTURES[*]}"
                            exit 1
                        fi
                    done
                    shift 2
                else
                    echo "Error: -t/--structures requires a value"
                    exit 1
                fi
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                echo "Error: Unknown option '$1'"
                echo "Use -h or --help for usage information"
                exit 1
                ;;
        esac
    done
}

# Function to log messages
log_message() {
    echo "$(date): $1" | tee -a "$LOG_FILE"
}

# Function to count currently used CPU cores
count_used_cores() {
    local total_cores=0
    
    # Get all mpirun processes and extract core counts
    while IFS= read -r line; do
        if [[ "$line" =~ mpirun.*-np[[:space:]]+([0-9]+) ]]; then
            local cores="${BASH_REMATCH[1]}"
            total_cores=$((total_cores + cores))
        elif [[ "$line" =~ mpirun.*-n[[:space:]]+([0-9]+) ]]; then
            local cores="${BASH_REMATCH[1]}"
            total_cores=$((total_cores + cores))
        fi
    done < <(ps aux | grep mpirun | grep -v grep)
    
    echo "$total_cores"
}

# Function to get available cores
get_available_cores() {
    local used_cores=$(count_used_cores)
    local remaining_cores=$((TOTAL_SYSTEM_CORES - used_cores))
    local available_cores=$((remaining_cores < MAX_OUR_CORES ? remaining_cores : MAX_OUR_CORES))
    
    if [[ $available_cores -lt 0 ]]; then
        available_cores=0
    fi
    
    echo "$available_cores"
}

# Pre-flight slot check and logging (before mpirun)
preflight_slots_check() {
    local visible=$(nproc)
    local used=$(count_used_cores)
    local available=$((visible - used))
    if [[ $available -lt 0 ]]; then available=0; fi
    log_message "Pre-flight slots: visible=$visible, used=$used, available=$available, need=$NEB_CORES_PER_JOB, oversubscribe=ON"
    if [[ $available -lt $NEB_CORES_PER_JOB ]]; then
        log_message "WARNING: available slots ($available) < required ($NEB_CORES_PER_JOB); proceeding due to --oversubscribe"
    else
        log_message "Pre-flight check OK"
    fi
}

# Function to process final.cfg to final.txt
process_final_cfg() {
    local task_dir="$1"
    local final_cfg="$task_dir/final.cfg"
    local final_txt="$task_dir/final.txt"
    
    if [[ -f "$final_cfg" ]]; then
        # Remove lines 1-3 and 5-9, keep line 4 and 10+
        sed -e '1,3d' -e '5,9d' "$final_cfg" > "$final_txt"
        local task_name=$(basename "$task_dir")
        log_message "Processed final.cfg -> final.txt for $task_name"
        return 0
    else
        local task_name=$(basename "$task_dir")
        log_message "ERROR: final.cfg not found in $task_name"
        return 1
    fi
}

# Function to check if in.neb is ready to run
is_neb_ready() {
    local task_dir="$1"
    
    # Check if in.min completed (final.cfg exists)
    if [[ ! -f "$task_dir/final.cfg" ]]; then
        return 1
    fi
    
    # Check if in.neb input exists
    if [[ ! -f "$task_dir/in.neb" ]]; then
        # Copy in.neb template if it doesn't exist
        local template_neb="dislocation/practice_dislocation/v3_trial3/NEB_new/edge_b100_p100_NEB/in.neb"
        if [[ -f "$template_neb" ]]; then
            cp "$template_neb" "$task_dir/"
            local task_name=$(basename "$task_dir")
            log_message "Copied in.neb template to $task_name"
        else
            log_message "ERROR: in.neb template not found"
            return 1
        fi
    fi
    
    # Check if NEB is already completed
    # NEB is truly completed when screen.* files contain "Total wall time:"
    local screen_files=($(find "$task_dir" -name "screen.*" 2>/dev/null))
    for screen_file in "${screen_files[@]}"; do
        if [[ -f "$screen_file" ]] && grep -q "Total wall time:" "$screen_file" 2>/dev/null; then
            return 1  # Already completed
        fi
    done
    
    # Check if this task is already running in our job list
    for job_id in "${!RUNNING_JOBS[@]}"; do
        if [[ "${RUNNING_JOBS[$job_id]}" == "$task_dir" ]]; then
            return 1  # Already running
        fi
    done
    
    return 0
}

# Function to run in.neb task
run_neb_task() {
    local task_dir="$1"
    local job_id="$2"
    
    local task_name=$(basename "$task_dir")
    log_message "Starting in.neb for $task_name (Job ID: $job_id)"
    
    cd "$task_dir" || return 1
    
    # Process final.cfg to final.txt first
    process_final_cfg "$task_dir"
    
    # Copy SNAP files if they don't exist
    local snap_coeff="../../../../potentials/HEA_v3_trial3.snapcoeff"
    local snap_param="../../../../potentials/HEA_v3_trial3.snapparam"
    
    if [[ -f "$snap_coeff" ]]; then
        cp "$snap_coeff" "$task_dir/"
        log_message "Copied SNAP coefficient file to $task_name"
    else
        log_message "ERROR: SNAP coefficient file not found at $snap_coeff"
        return 1
    fi
    
    if [[ -f "$snap_param" ]]; then
        cp "$snap_param" "$task_dir/"
        log_message "Copied SNAP parameter file to $task_name"
    else
        log_message "ERROR: SNAP parameter file not found at $snap_param"
        return 1
    fi
    # Prevent duplicate launches in the same task directory
    local existing_pid
    existing_pid=$(for pn in mpirun orterun; do ps -C "$pn" -o pid= --no-headers; done | while read p; do
        if [[ "$(readlink -f /proc/$p/cwd 2>/dev/null)" == "$task_dir" ]]; then
            echo "$p"; break;
        fi
    done)
    if [[ -n "$existing_pid" ]]; then
        log_message "NEB already running for $task_name (PID: $existing_pid); skipping new launch"
        cd - >/dev/null
        return 0
    fi

    # Run the NEB task: write to a unique screen file per launch to avoid collisions
    local screen_file="screen.${job_id}"
    nohup /home/jhenyu/opt/openmpi-4.1.5/bin/mpirun --bind-to none --map-by slot -np "$NEB_CORES_PER_JOB" "$LAMMPS_EXE" \
        -partition ${LOOP}x${CORE} -in in.neb >> "$screen_file" 2>&1 &
    
    local pid=$!
    RUNNING_JOBS[$job_id]="$task_dir"
    JOB_PIDS[$job_id]=$pid
    JOB_CORES[$job_id]=$NEB_CORES_PER_JOB
    
    log_message "Started in.neb for $task_name (PID: $pid, Cores: $NEB_CORES_PER_JOB)"
    
    cd - >/dev/null
}

# Function to scan for completed in.min tasks
scan_for_completed_min() {
    local completed_tasks=()
    local lr_count=0
    local next_count=0
    
    for slip_system in "${SLIP_SYSTEMS[@]}"; do
        slip_dir="$NEB_ROOT/$slip_system"
        if [[ ! -d "$slip_dir" ]]; then
            continue
        fi
        
        # Find specified structure directories
        for structure in "${STRUCTURES[@]}"; do
            structure_dir="$slip_dir/$structure"
            if [[ ! -d "$structure_dir" ]]; then
                continue
            fi
            
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
                    if [[ -f "$lr_dir/final.cfg" ]]; then
                        # Check if in.neb is ready to run
                        if is_neb_ready "$lr_dir"; then
                            # Check if not already running
                            local already_running=false
                            for job_id in "${!RUNNING_JOBS[@]}"; do
                                if [[ "${RUNNING_JOBS[$job_id]}" == "$lr_dir" ]]; then
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
                        
                        # Check if in.min completed (final.cfg exists)
                        if [[ -f "$next_dir/final.cfg" ]]; then
                            # Check if in.neb is ready to run
                            if is_neb_ready "$next_dir"; then
                                # Check if not already running
                                local already_running=false
                                for job_id in "${!RUNNING_JOBS[@]}"; do
                                    if [[ "${RUNNING_JOBS[$job_id]}" == "$next_dir" ]]; then
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

# Function to monitor running jobs
monitor_running_jobs() {
    for job_id in "${!RUNNING_JOBS[@]}"; do
        local task_dir="${RUNNING_JOBS[$job_id]}"
        local pid="${JOB_PIDS[$job_id]}"
        
        # Check if process is still running
        if ! kill -0 "$pid" 2>/dev/null; then
            log_message "NEB job $job_id (PID: $pid) has finished"
            
            # Check if NEB completed successfully (look for "Total wall time:" in screen.* files)
            local task_name=$(basename "$task_dir")
            local screen_files=($(find "$task_dir" -name "screen.*" 2>/dev/null))
            local found_completion=false
            for screen_file in "${screen_files[@]}"; do
                if [[ -f "$screen_file" ]] && grep -q "Total wall time:" "$screen_file" 2>/dev/null; then
                    log_message "SUCCESS: $task_name NEB completed successfully"
                    found_completion=true
                    break
                fi
            done
            if [[ "$found_completion" == false ]]; then
                log_message "WARNING: $task_name NEB finished but no completion marker found"
            fi
            
            # Clean up
            unset RUNNING_JOBS[$job_id]
            unset JOB_PIDS[$job_id]
            unset JOB_CORES[$job_id]
        fi
    done
}

# Function to count running NEB jobs and cores
count_running_neb() {
    local job_count=0
    local total_cores=0
    
    for job_id in "${!RUNNING_JOBS[@]}"; do
        ((job_count++))
        total_cores=$((total_cores + JOB_CORES[$job_id]))
    done
    
    echo "$job_count $total_cores"
}

# Function to cleanup on exit
cleanup() {
    log_message "Shutting down NEB scheduler..."
    
    # Kill all running NEB jobs
    for job_id in "${!JOB_PIDS[@]}"; do
        local pid="${JOB_PIDS[$job_id]}"
        if kill -0 "$pid" 2>/dev/null; then
            log_message "Terminating NEB job $job_id (PID: $pid)"
            kill "$pid" 2>/dev/null
        fi
    done
    
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Function to generate unique job ID
generate_job_id() {
    echo "neb_$(date +%s)_$$_${RANDOM}_${RANDOM}"
}

# Main loop
main_loop() {
    log_message "Starting NEB scheduler"
    log_message "Total system cores: $TOTAL_SYSTEM_CORES, Our max cores: $MAX_OUR_CORES, Cores per NEB job: $NEB_CORES_PER_JOB"
    log_message "Max concurrent NEB jobs: $((MAX_OUR_CORES / NEB_CORES_PER_JOB))"
    log_message "Selected slip systems: ${SLIP_SYSTEMS[*]}"
    log_message "Selected structures: ${STRUCTURES[*]}"
    
    while true; do
        # Monitor existing jobs
        monitor_running_jobs
        
        # Count current running NEB jobs
        read -r neb_jobs neb_cores <<< "$(count_running_neb)"
        
        # Get available cores
        local available_cores=$(get_available_cores)
        local system_cores=$(count_used_cores)
        local remaining_system=$((TOTAL_SYSTEM_CORES - system_cores))
        
        log_message "System cores used: $system_cores/$TOTAL_SYSTEM_CORES, Remaining: $remaining_system, Our limit: $MAX_OUR_CORES, Available: $available_cores, NEB jobs: $neb_jobs"
        
        # Check if we can start more NEB jobs
        if [[ $available_cores -ge $NEB_CORES_PER_JOB ]]; then
            # Scan for completed in.min tasks
            local completed_tasks=($(scan_for_completed_min))
            
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
                # Check if we still have enough cores
                local current_available=$(get_available_cores)
                if [[ $current_available -lt $NEB_CORES_PER_JOB ]]; then
                    log_message "Not enough cores available ($current_available < $NEB_CORES_PER_JOB)"
                    break
                fi
                
                # Generate job ID and start NEB task
                local job_id=$(generate_job_id)
                run_neb_task "$task_dir" "$job_id"
                
                # Brief pause between job starts
                sleep 5
            done
            
            # Process next_* tasks (lower priority)
            for task_dir in "${next_tasks[@]}"; do
                # Check if we still have enough cores
                local current_available=$(get_available_cores)
                if [[ $current_available -lt $NEB_CORES_PER_JOB ]]; then
                    log_message "Not enough cores available ($current_available < $NEB_CORES_PER_JOB)"
                    break
                fi
                
                # Generate job ID and start NEB task
                local job_id=$(generate_job_id)
                run_neb_task "$task_dir" "$job_id"
                
                # Brief pause between job starts
                sleep 5
            done
            
            # Log task distribution
            if [[ ${#lr_tasks[@]} -gt 0 || ${#next_tasks[@]} -gt 0 ]]; then
                log_message "Found ${#lr_tasks[@]} L*_R* tasks, ${#next_tasks[@]} next_* tasks ready for execution"
                # Also print the exact ready lists for visibility
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
        else
            log_message "Not enough cores available for new NEB jobs ($available_cores < $NEB_CORES_PER_JOB)"
        fi
        
        sleep "$SCAN_INTERVAL"
    done
}

# Parse command line arguments
parse_arguments "$@"

# Run main loop
main_loop
