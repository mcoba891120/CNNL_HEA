#!/bin/bash

# Set trial number and initial GPU
TRIAL_NUM=3
NUM_GPU=2
TEMPERATURE=1273

# Define base directories
BASE_DIR="/work/cnnltmp01/mcoba891120"
DISLOCATION_FIX_DIR="${BASE_DIR}/dislocation_fix"
TRIAL_DIR="${DISLOCATION_FIX_DIR}/v3_trial3"
LAMMPS_PATH_GPU04=~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100
LAMMPS_PATH_GPU03=~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_p100
LAMMPS_PATH=$LAMMPS_PATH_GPU03
SESSION_PATH="dislocation_fix/v3_trail3_MC${TEMPERATURE}k"



# Create necessary directories
mkdir -p $SESSION_PATH


# Configuration array
declare -A configs=(
    # Edge configurations
    # ["edge_100_100"]="edge 100 100 17 18 18"
    ["edge_100_110"]="edge 100 110 17 12 12"
    ["edge_110_110"]="edge 110 110 12 17 12"
    # ["edge_110_100"]="edge 110 100 12 12 17"
    # ["edge_111_110"]="edge 111 110 10 7 12"
    # # Screw configurations
    # ["screw_100_100"]="screw 100 100 17 18 18"
    # ["screw_100_110"]="screw 100 110 12 17 12"
    # ["screw_110_110"]="screw 110 110 17 12 12"
    # ["screw_110_100"]="screw 110 100 12 12 17"
    # ["screw_111_110"]="screw 111 110 7 10 12"
)

# Check if LAMMPS_PATH is set
if [ -z "$LAMMPS_PATH" ]; then
    echo "Error: LAMMPS_PATH environment variable is not set"
    exit 1
fi

# Change to working directory
cd $SESSION_PATH || {
    echo "Error: Failed to change to directory $TRIAL_DIR"
    exit 1
}

# Function to handle errors
handle_error() {
    echo "Error: $1"
    exit 1
}

# Main processing loop
for config_name in "${!configs[@]}"; do
    # Parse configuration
    read -r dislocation_type b p x y z <<< "${configs[$config_name]}" || handle_error "Failed to parse configuration"
    
    # Create and enter configuration directory
    config_dir="${dislocation_type}_b${b}_p${p}"
    mkdir -p "$config_dir"
    cd "$config_dir" || handle_error "Failed to enter directory $config_dir"
    
    # Copy necessary files
    cp "$TRIAL_DIR/$config_dir/MD_${TEMPERATURE}K_relax/after_relax_bulk.data" . || handle_error "Failed to copy data file"
    cp "../../../in.swap.HEA" . || handle_error "Failed to copy HEA file"
    
    # Modify the input file
    sed -i \
        -e "s|{{trial_num}}|$TRIAL_NUM|g" \
        -e "s|{{temperature}}|$TEMPERATURE|g" \
        -e "s|{{input_file}}|./after_relax_bulk.data|g" \
        "in.swap.HEA" || handle_error "Failed to modify in.swap.HEA"
    
    # Log processing information
    echo "Processing: $config_name (${configs[$config_name]})"
    echo "Using GPU: $NUM_GPU"
    
    # Set GPU and run LAMMPS
    export CUDA_VISIBLE_DEVICES=$NUM_GPU
    
    # Run LAMMPS with error checking
    nohup mpirun -np 1 -cpu-set "$NUM_GPU" "$LAMMPS_PATH" \
        -k on g 1 -sf kk -pk kokkos newton on neigh half \
        -log none -in in.swap.HEA > STDOUT 2>&1 &
    
    # Check if the process started successfully
    if [ $? -ne 0 ]; then
        handle_error "Failed to start LAMMPS process for $config_name"
    fi
    
    echo "Completed: $config_name"
    echo "----------------------------------------"
    
    # Update GPU number
    NUM_GPU=$((NUM_GPU + 1))
    # if [ "$NUM_GPU" -eq 2 ]; then
    #     NUM_GPU=3
    # fi
    
    # Return to parent directory
    cd ../ || handle_error "Failed to return to trial directory"
    
    # Wait between iterations
    sleep 2
done

echo "All configurations completed successfully"
exit 0