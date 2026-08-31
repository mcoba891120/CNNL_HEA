#!/bin/bash
VERSION=5
TRIAL=4
RUN=100000
USER_DIR="/work/cnnltmp01/mcoba891120"
ALLOY="NiCoTiZrHf"

for t in "300" "600" "900" ; do
    for slip_system in "b100p110" "b111p110" ; do
        folder_name="v${VERSION}_trial${TRIAL}_9792_${t}k_${slip_system}"
        mkdir -p "$folder_name"
        cd "$folder_name"
        cp "relaxation/templates/in.relax.5quinary.var.NiCoTiZrHf" .
        
        # Corrected if condition
        if [ "$slip_system" = "b100p110" ]; then
            STRUCTURE_PATH="relaxation/NiCoTiZrHf_110/5quinary/NiCoTiZrHf_b100p110.data"
        else
            STRUCTURE_PATH="relaxation/NiCoTiZrHf_110/5quinary/NiCoTiZrHf_b111p110.data"
        fi
        
        # Use folder_name instead of undefined SESSION_NAME
        sed -e "s|{{structure_path}}|${STRUCTURE_PATH}|g" \
            -e "s|{{var_num}}|$TRIAL|g" \
            -e "s|{{session_name}}|$folder_name|g" \
            -e "s|{{run}}|$RUN|g" \
            -e "s|{{temperature}}|$t|g" \
            -e "s|{{user_dir}}|$USER_DIR|g" \
            "in.relax.5quinary.var.$ALLOY" > "in.relax.$ALLOY.$folder_name"
        
        # Run LAMMPS with unique output file to avoid overwriting
        nohup mpirun -np 50 ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in "in.relax.$ALLOY.$folder_name" > "STDOUT_${folder_name}" 2>&1 &
        
        cd ../
    done
done