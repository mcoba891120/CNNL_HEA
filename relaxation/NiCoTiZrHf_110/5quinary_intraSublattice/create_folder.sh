#!/bin/bash

# Create a series of folders fo v3_trial3_9792 under different temperature and slip system and finally put the corresponding SS_curve files into the folder
for mc_temperature in "" "mc300k" "mc1273k" ; do
    for temperature in "300k" "600k" "900k" ; do
        for slip_system in "b100p110" "b111p110" ;do
          
            # Move the SS_curve files into the folder
            if [ "$mc_temperature" = "" ] ; then
                echo "No MC temperature"
            #     folder_name="v3_trial3_9792_${temperatue}_${slip_system}"
            #     mkdir -p "$folder_name"
            #     mv "SS_curve_v3_trial3_${temperatue}_${slip_system}.txt" "$folder_name/SS_curve_v3_trial3_${temperatue}_${slip_system}.txt"
            elif [ "$mc_temperature" = "mc300k" ] ; then
                folder_name="v3_trial3_9792_${temperature}_${mc_temperature}_${slip_system}"
                mkdir -p "$folder_name"
                cd "$folder_name"
                cp "monte_carlo/MC_5quinary/NiCoTiZrHf_110_intraSubLattice/v3_trial3_9792_300k_${slip_system}/mc_folder/emin.data" .
                cp "relaxation/NiCoTiZrHf_110/5quinary/${folder_name}/in.relax.NiCoTiZrHf.${folder_name}" .
                atomsk emin.data -duplicate 2 1 1 lmp temp.lmp && mv temp.lmp emin_duplicated.data
                nohup mpirun -np 20 ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.relax.NiCoTiZrHf.${folder_name} > STDOUT &
                cd ../
            elif [ "$mc_temperature" = "mc1273k" ] ; then
                folder_name="v3_trial3_9792_${temperature}_${mc_temperature}_${slip_system}"
                mkdir -p "$folder_name"
                cd "$folder_name"
                cp "monte_carlo/MC_5quinary/NiCoTiZrHf_110_intraSubLattice/v3_trial3_9792_1273k_${slip_system}/mc_folder/emin.data" .
                cp "relaxation/NiCoTiZrHf_110/5quinary/${folder_name}/in.relax.NiCoTiZrHf.${folder_name}" .
                atomsk emin.data -duplicate 2 1 1 lmp temp.lmp && mv temp.lmp emin_duplicated.data
                nohup mpirun -np 20 ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.relax.NiCoTiZrHf.${folder_name} > STDOUT &
                cd ../
            fi

        done
    done
done