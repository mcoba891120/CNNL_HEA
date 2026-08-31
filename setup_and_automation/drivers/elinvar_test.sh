#!/bin/bash

read -p "Enter session name: " SESSION_NAME
read -p "Enter the PE number: " VAR_NUM

# Set default values
DEFAULT_SIMULATION_MODE="compress"
DEFAULT_ALLOY="NiCoTiZrHf"
DEFAULT_VAR_NUM=$VAR_NUM

# Prompt user for inputs
read -p "Enter number of cores (default is 34): " DEFAULT_CORE
DEFAULT_CORE=${DEFAULT_CORE:-34}

read -p "Enter number of runs (default is 10000): " DEFAULT_RUN
DEFAULT_RUN=${DEFAULT_RUN:-10000}

read -p "Enter start temperature (default is 300): " DEFAULT_START_TEMP
DEFAULT_START_TEMP=${DEFAULT_START_TEMP:-300}

read -p "Enter end temperature (default is 300): " DEFAULT_END_TEMP
DEFAULT_END_TEMP=${DEFAULT_END_TEMP:-300}

DEFAULT_TEMP_STEP=300

# Read configuration from file if it exists
CONFIG_FILE="auto_run_config.txt"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Use default values or values from config file, but allow override from command line
SIMULATION_MODE=${1:-${SIMULATION_MODE:-$DEFAULT_SIMULATION_MODE}}
ALLOY=${2:-${ALLOY:-$DEFAULT_ALLOY}}
VAR_NUM=${3:-${VAR_NUM:-$DEFAULT_VAR_NUM}}
CORE=${4:-${CORE:-$DEFAULT_CORE}}
RUN=${5:-${RUN:-$DEFAULT_RUN}}
START_TEMP=${6:-${START_TEMP:-$DEFAULT_START_TEMP}}
TEMP_STEP=${7:-${TEMP_STEP:-$DEFAULT_TEMP_STEP}}
END_TEMP=${8:-${END_TEMP:-$DEFAULT_END_TEMP}}

# Array of orientations: "X Y Z" grid size per orientation.
# Override from auto_run_config.txt (or env) with e.g.:
#   ORIENTATIONS_100="30 15 15"
#   ORIENTATIONS_111="24 20 12"
#   ACTIVE_ORIENTATIONS="100 111"
declare -A ORIENTATIONS
ORIENTATIONS[100]=${ORIENTATIONS_100:-"30 15 15"}
ORIENTATIONS[110]=${ORIENTATIONS_110:-"21 10 15"}
ORIENTATIONS[111]=${ORIENTATIONS_111:-"24 20 12"}

# Which orientations to actually run this session (default: all defined above).
read -a ACTIVE_ORIENTATIONS <<< "${ACTIVE_ORIENTATIONS:-100 110 111}"

# Optional label appended to the run/session name (e.g. "mc300k"); empty by default.
RUN_LABEL=${RUN_LABEL:-}

# Function to calculate total atoms based on orientation
calculate_total_atoms() {
    local orientation=$1
    local x=$2
    local y=$3
    local z=$4
    
    case $orientation in
        100) echo $((x * y * z * 2)) ;;
        110) echo $((x * y * z * 4)) ;;
        111) echo $((x * y * z * 12)) ;;
        *) echo "Invalid orientation"; exit 1 ;;
    esac
}

# Function to run the simulation
run_simulation() {
    local orientation=$1
    local temp=$2
    local session_name=$SESSION_NAME
    
    # Get X, Y, Z values for the orientation
    read X Y Z <<< "${ORIENTATIONS[$orientation]}"
    
    local total_atoms=$(calculate_total_atoms $orientation $X $Y $Z)
    
    # Create a temporary input file
    local input_file="temp_input_${orientation}_${temp}.txt"
cat << EOF > "$input_file"
$SIMULATION_MODE
$ALLOY
$orientation
${session_name}_${total_atoms}_${temp}k${RUN_LABEL:+_${RUN_LABEL}}
$X $Y $Z
$VAR_NUM
$CORE
$RUN
$temp
EOF

    echo "Running simulation for orientation: ${orientation} (${X}x${Y}x${Z}), temperature: ${temp}K"
    cat "$input_file" | ../auto_simulation.sh

    # Clean up
    rm "$input_file"
}

# Main execution
for orientation in "${ACTIVE_ORIENTATIONS[@]}"; do
    if [ "$SIMULATION_MODE" = "compress" ]; then
        for temp in $(seq $START_TEMP $TEMP_STEP $END_TEMP); do
            run_simulation $orientation $temp
        done
    else
        run_simulation $orientation $START_TEMP
    fi
done

echo "All simulations completed."
