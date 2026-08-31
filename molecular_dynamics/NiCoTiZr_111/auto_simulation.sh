#!/bin/bash
read -p "Enter the session name: " SESSION_NAME
read -p "Enter the orientation(100, 111)" ORIENTATION
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
STRUCTURE_NAME="NiCoTiZr_$TOTAL_ATOM"
STRUCTURE_PATH="../structure/$STRUCTURE_NAME.lmp"
mkdir -p structure
mkdir -p $SESSION_NAME

if [ ! -f "structure/$STRUCTURE_NAME.pos" ]; then
    if [ -f "POSCAR" ]; then
        rm POSCAR
    fi

    echo "y" | atomsk --create CsCl 3.0 Ni Ti orient $ORIENTATION_STRING -duplicate $X $Y $Z pos

    mv POSCAR "$STRUCTURE_NAME.pos"
    mv "$STRUCTURE_NAME.pos" structure/
    python HEA_gen.py $STRUCTURE_NAME $TOTAL_ATOM
    if [ $? -eq 0 ]; then
        echo "success"
    else
        echo "fail"
        exit 1
    fi
    mv $STRUCTURE_NAME.lmp structure/
    echo "Structure generated and moved to structure/ directory."
else
    echo "Structure file '$STRUCTURE_NAME.pos' already exists in the 'structure' directory."
fi

cd ./$SESSION_NAME
CURRENT_DIRECTORY=$(pwd)
cp relaxation/templates/in.relax.var.NiCoTiZr .
sed -e "s|{{structure_path}}|$STRUCTURE_PATH|g" \
    -e "s|{{var_num}}|$VAR_NUM|g" \
    -e "s|{{session_name}}|$SESSION_NAME|g" \
    -e "s|{{run}}|$RUN|g" \
    in.relax.var.NiCoTiZr > in.relax.NiCoTiZr
echo "cd $CURRENT_DIRECTORY"
echo "nohup mpirun -np $CORE /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.relax.NiCoTiZr > STDOUT &"
ssh amd01
exit 0
# since it will not find mpirun command so the below command still need to do manually
# ssh cnnltmp01@amd01 "cd $CURRENT_DIRECTORY && nohup mpirun -np $CORE /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.relax.NiCoTiZr > STDOUT &"
