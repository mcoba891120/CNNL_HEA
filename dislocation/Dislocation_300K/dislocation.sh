#!/bin/bash

USER_DIR=$(pwd)
read -p "Enter the simulation mode(with, without) dislocation: " SIMULATION_MODE

DEFAULT_ALLOY="NiCoTiZrHf"
read -p "Enter the alloy (default: $DEFAULT_ALLOY): " ALLOY
ALLOY=${ALLOY:-$DEFAULT_ALLOY}

read -p "Enter the dislocation type (edge, screw): " DISLOCATION_TYPE

read -p "Enter the b(100, 110, 111): " B
DEFAULT_B=100
B=${B:-$DEFAULT_B}

read -p "Enter the p (100, 110, 111): " P

SESSION_NAME="${DISLOCATION_TYPE}_b${B}_p${P}"

############################################################################
# Create simulation mode directory if it doesn't exist
if [ ! -d "$SIMULATION_MODE" ]; then
    mkdir -p "$SIMULATION_MODE"
fi

cd "$SIMULATION_MODE" || exit 1

############################################################################
read -p "Enter the duplication of X, Y, Z: " X Y Z

if [ "$DISLOCATION_TYPE" = "edge" ] && [ "$B" -eq 100 ] && [ "$P" -eq 100 ]; then
    TOTAL_ATOM=$((X*Y*Z*2))
    ORIENTATION_STRING="[100] [010] [001]"

elif [ "$DISLOCATION_TYPE" = "screw" ] && [ "$B" -eq 100 ] && [ "$P" -eq 100 ]; then
    TOTAL_ATOM=$((X*Y*Z*2))
    ORIENTATION_STRING="[100] [010] [001]"
##################################################
elif [ "$DISLOCATION_TYPE" = "edge" ] && [ "$B" -eq 110 ] && [ "$P" -eq 100 ]; then
    TOTAL_ATOM=$((X*Y*Z*4))
    ORIENTATION_STRING="[1-10] [110] [001]"

elif [ "$DISLOCATION_TYPE" = "screw" ] && [ "$B" -eq 110 ] && [ "$P" -eq 100 ]; then
    TOTAL_ATOM=$((X*Y*Z*4))
    ORIENTATION_STRING="[1-10] [110] [001]"
##################################################
elif [ "$DISLOCATION_TYPE" = "edge" ] && [ "$B" -eq 110 ] && [ "$P" -eq 110 ]; then
    TOTAL_ATOM=$((X*Y*Z*4))
    ORIENTATION_STRING="[101] [010] [10-1]"

elif [ "$DISLOCATION_TYPE" = "edge" ] && [ "$B" -eq 100 ] && [ "$P" -eq 110 ]; then
    TOTAL_ATOM=$((X*Y*Z*4))
    ORIENTATION_STRING="[100] [01-1] [011]"
##################################################
elif [ "$DISLOCATION_TYPE" = "screw" ] && [ "$B" -eq 100 ] && [ "$P" -eq 110 ]; then
    TOTAL_ATOM=$((X*Y*Z*4))
    ORIENTATION_STRING="[10-1] [010] [101]"

elif [ "$DISLOCATION_TYPE" = "screw" ] && [ "$B" -eq 110 ] && [ "$P" -eq 110 ]; then
    TOTAL_ATOM=$((X*Y*Z*4))
    ORIENTATION_STRING="[100] [011] [01-1]"
##################################################
elif [ "$DISLOCATION_TYPE" = "edge" ] && [ "$B" -eq 111 ] && [ "$P" -eq 110 ]; then
    TOTAL_ATOM=$((X*Y*Z*12))
    ORIENTATION_STRING="[111] [2-1-1] [0-11]"

elif [ "$DISLOCATION_TYPE" = "screw" ] && [ "$B" -eq 111 ] && [ "$P" -eq 110 ]; then
    TOTAL_ATOM=$((X*Y*Z*12))
    ORIENTATION_STRING="[2-1-1] [111] [0-11]"
##################################################
else
    echo "Invalid orientation"
    exit 1
fi

#######################################################################################################
read -p "Enter the PE number: " VAR_NUM
read -p "Enter the core to use (cpu): " CORE
read -p "Enter the number of core to use (gpu): " GPU_CORE
read -p "Enter the number of runs: " RUN
DEFAULT_TEMPERATURE="300"
read -p "Enter the temperature(default: $DEFAULT_TEMPERATURE k): " TEMPERATURE
TEMPERATURE=${TEMPERATURE:-$DEFAULT_TEMPERATURE}

STRUCTURE_NAME="${ALLOY}_${DISLOCATION_TYPE}_${TOTAL_ATOM}"
mkdir -p structure
mkdir -p "$SESSION_NAME"


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

cd structure
rm "$STRUCTURE_NAME.pos"
cd .. 

echo "Structure generated and moved to structure/ directory."


cd "./$SESSION_NAME" || exit 1
CURRENT_DIRECTORY=$(pwd)

if [ "$SIMULATION_MODE" = "without" ]; then
    STRUCTURE_PATH="../structure/$STRUCTURE_NAME.lmp"
    cp "$USER_DIR/in.relax_HEA.var.$ALLOY" .                               # var
    sed -e "s|{{structure_path}}|$STRUCTURE_PATH|g" \
        -e "s|{{var_num}}|$VAR_NUM|g" \
        -e "s|{{session_name}}|$SESSION_NAME|g" \
        -e "s|{{run}}|$RUN|g" \
        -e "s|{{temperature}}|$TEMPERATURE|g" \
        -e "s|{{user_dir}}|$USER_DIR|g" \
        "in.relax_HEA.var.$ALLOY" > "in.relax_HEA.$ALLOY.$SESSION_NAME"
elif [ "$SIMULATION_MODE" = "with" ]; then
    
    if [ "$DISLOCATION_TYPE" = "edge" ]; then
        cd ../structure
        bash "$USER_DIR/build.$ALLOY.sh" "$STRUCTURE_NAME" "$STRUCTURE_PATH" "$SESSION_NAME" "$X"
        if [ $? -eq 0 ]; then
            echo "success"
            cd ../$SESSION_NAME
        else
            echo "fail"
            exit 1
        fi

        STRUCTURE_PATH="${STRUCTURE_NAME}_init_edge.data"
        if [ ! -f "$STRUCTURE_PATH" ]; then
        echo "edge haven't been done"
        exit 1
        fi
        cp "$USER_DIR/in.relax_HEA.var.$ALLOY" .                               # var
        sed -e "s|{{structure_path}}|$STRUCTURE_PATH|g" \
            -e "s|{{var_num}}|$VAR_NUM|g" \
            -e "s|{{session_name}}|$SESSION_NAME|g" \
            -e "s|{{run}}|$RUN|g" \
            -e "s|{{temperature}}|$TEMPERATURE|g" \
            -e "s|{{user_dir}}|$USER_DIR|g" \
            "in.relax_HEA.var.$ALLOY" > "in.relax_HEA.$ALLOY.$SESSION_NAME"

    elif [ "$DISLOCATION_TYPE" = "screw" ]; then
        STRUCTURE_PATH="../structure/$STRUCTURE_NAME.lmp"
        cp "$USER_DIR/in.screw.var.$ALLOY" .
        sed -e "s|{{structure_path}}|$STRUCTURE_PATH|g" \
            -e "s|{{structure_name}}|$STRUCTURE_NAME|g" \
            -e "s|{{Y}}|$Y|g" \
            "in.screw.var.$ALLOY" > "in.screw.$ALLOY.$SESSION_NAME"

        if [ "$(hostname)" = "amd01" ]; then
            cd $CURRENT_DIRECTORY
            nohup mpirun -np 4 /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.screw.$ALLOY.$SESSION_NAME > STDOUT &
            echo "-----------------------------------------"
        elif [ "$(hostname)" = "gpu04" ]; then
            cd $CURRENT_DIRECTORY
            export CUDA_VISIBLE_DEVICES=$GPU_CORE
            nohup mpirun -np 1 -cpu-set 0 ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -k on g 1 -sf kk -pk kokkos newton on neigh half -in in.screw.$ALLOY.$SESSION_NAME > STDOUT &
            echo "-----------------------------------------"
        else
            echo "fail"
            exit 1
        fi

        sleep 5

        STRUCTURE_PATH="${STRUCTURE_NAME}_init_screw.data"
        if [ ! -f "$STRUCTURE_PATH" ]; then
        echo "screw haven't been done"
        exit 1
        fi
        cp "$USER_DIR/in.relax_HEA.var.$ALLOY" .                               # var
        sed -e "s|{{structure_path}}|$STRUCTURE_PATH|g" \
            -e "s|{{var_num}}|$VAR_NUM|g" \
            -e "s|{{session_name}}|$SESSION_NAME|g" \
            -e "s|{{run}}|$RUN|g" \
            -e "s|{{temperature}}|$TEMPERATURE|g" \
            -e "s|{{user_dir}}|$USER_DIR|g" \
            "in.relax_HEA.var.$ALLOY" > "in.relax_HEA.$ALLOY.$SESSION_NAME"

    fi

fi


if [ "$(hostname)" = "amd01" ]; then
    cd $CURRENT_DIRECTORY
    nohup mpirun -np $CORE /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.relax_HEA.$ALLOY.$SESSION_NAME > STDOUT &
    echo "-----------------------------------------"
    echo "Info of this session: "
    ps aux | grep in.relax_HEA.$ALLOY.$SESSION_NAME
    echo "-----------------------------------------"
    echo "Info of all session: "
    ps aux | grep mpirun
elif [ "$(hostname)" = "sophon" ]; then
    echo "ssh to amd01 and run the following command:"
    echo "cd $CURRENT_DIRECTORY"
    echo "nohup mpirun -np $CORE /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.$SIMULATION_MODE.$ALLOY.$SESSION_NAME > STDOUT &"
elif [ "$(hostname)" = "gpu04" ]; then
    cd $CURRENT_DIRECTORY
    export CUDA_VISIBLE_DEVICES=$GPU_CORE
    nohup mpirun -np 1 -cpu-set 0 ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -k on g 1 -sf kk -pk kokkos newton on neigh half -in in.relax_HEA.$ALLOY.$SESSION_NAME > STDOUT &
    echo "-----------------------------------------"
    echo "Info of this session: "
    ps aux | grep in.relax_HEA.$ALLOY.$SESSION_NAME
    echo "-----------------------------------------"
    echo "Info of all session: "
    ps aux | grep mpirun
fi


exit 0