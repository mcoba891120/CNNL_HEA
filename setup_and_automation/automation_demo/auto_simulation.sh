#!/bin/bash

USER_DIR=$(pwd)
read -p "Enter the simulation mode(relax, heat, compress): " SIMULATION_MODE
DEFAULT_ALLOY="NiCoTiZr"
read -p "Enter the alloy (default: $DEFAULT_ALLOY): " ALLOY
ALLOY=${ALLOY:-$DEFAULT_ALLOY}
read -p "Enter the orientation(100, 111)" ORIENTATION
DEFAULT_ORIENTATION=100
ORIENTATION=${ORIENTATION:-$DEFAULT_ORIENTATION}
ALLOY_ORIENTATION="${ALLOY}_${ORIENTATION}"

# Create simulation mode directory if it doesn't exist
if [ ! -d "$SIMULATION_MODE" ]; then
    mkdir -p "$SIMULATION_MODE"
fi

cd "$SIMULATION_MODE" || exit 1

if [ ! -d "$ALLOY_ORIENTATION" ]; then
    mkdir -p "$ALLOY_ORIENTATION"
fi

cd "$ALLOY_ORIENTATION" || exit 1

read -p "Enter the session name: " SESSION_NAME
read -p "Enter the duplication of X, Y, Z: " X Y Z
if [ "$ORIENTATION" -eq 100 ]; then
    TOTAL_ATOM=$((X*Y*Z*2))
    ORIENTATION_STRING="[100] [010] [001]"
elif [ "$ORIENTATION" -eq 111 ]; then
    TOTAL_ATOM=$((X*Y*Z*12))
    ORIENTATION_STRING="[111] [1-10] [11-2]"
else
    echo "Invalid orientation"
    exit 1
fi

read -p "Enter the PE number: " VAR_NUM
read -p "Enter the core to use: " CORE
read -p "Enter the number of runs: " RUN
STRUCTURE_NAME="${ALLOY}_${TOTAL_ATOM}"
STRUCTURE_PATH="../structure/$STRUCTURE_NAME.lmp"
mkdir -p structure
mkdir -p "$SESSION_NAME"

if [ ! -f "structure/$STRUCTURE_NAME.pos" ]; then
    if [ -f "POSCAR" ]; then
        rm POSCAR
    fi

    echo "y" | atomsk --create CsCl 3.0 Ni Ti orient $ORIENTATION_STRING -duplicate $X $Y $Z pos

    mv POSCAR "$STRUCTURE_NAME.pos"
    mv "$STRUCTURE_NAME.pos" structure/
    python "$USER_DIR/HEA_gen.py" "$STRUCTURE_NAME" "$TOTAL_ATOM"
    if [ $? -eq 0 ]; then
        echo "success"
    else
        echo "fail"
        exit 1
    fi
    mv "$STRUCTURE_NAME.lmp" structure/
    echo "Structure generated and moved to structure/ directory."
else
    echo "Structure file '$STRUCTURE_NAME.pos' already exists in the 'structure' directory."
fi

cd "./$SESSION_NAME" || exit 1
CURRENT_DIRECTORY=$(pwd)

if [ "$SIMULATION_MODE" = "relax" ]; then
    cp "$USER_DIR/in.relax.var.$ALLOY" .
    sed -e "s|{{structure_path}}|$STRUCTURE_PATH|g" \
        -e "s|{{var_num}}|$VAR_NUM|g" \
        -e "s|{{session_name}}|$SESSION_NAME|g" \
        -e "s|{{run}}|$RUN|g" \
        -e "s|{{user_dir}}|$USER_DIR|g" \
        "in.relax.var.$ALLOY" > "in.relax.$ALLOY.$SESSION_NAME"
elif [ "$SIMULATION_MODE" = "compress" ]; then
    cp "$USER_DIR/in.compress.var.$ALLOY" .
    read -p "Enter the temperature: " TEMPERATURE
    sed -e "s|{{structure_path}}|$STRUCTURE_PATH|g" \
        -e "s|{{var_num}}|$VAR_NUM|g" \
        -e "s|{{session_name}}|$SESSION_NAME|g" \
        -e "s|{{run}}|$RUN|g" \
        -e "s|{{temperature}}|$TEMPERATURE|g" \
        -e "s|{{alloy}}|$ALLOY|g" \
        -e "s|{{user_dir}}|$USER_DIR|g" \
        "in.compress.var.$ALLOY" > "in.compress.$ALLOY.$SESSION_NAME"
fi

if [ "$(hostname)" = "amd01" ]; then
    cd $CURRENT_DIRECTORY
    nohup mpirun -np $CORE /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.$SIMULATION_MODE.$ALLOY.$SESSION_NAME > STDOUT &
    echo "-----------------------------------------"
    echo "Info of this session: "
    ps aux | grep in.$SIMULATION_MODE.$ALLOY.$SESSION_NAME
    echo "-----------------------------------------"
    echo "Info of all session: "
    ps aux | grep mpirun
elif [ "$(hostname)" = "sophon" ]; then
    echo "ssh to amd01 and run the following command:"
    echo "cd $CURRENT_DIRECTORY"
    echo "nohup mpirun -np $CORE /home/cnnltmp02/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.$SIMULATION_MODE.$ALLOY.$SESSION_NAME > STDOUT &"
fi

exit 0