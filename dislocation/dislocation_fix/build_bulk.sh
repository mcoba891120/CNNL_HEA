#!/bin/bash

current_path=$(pwd)
cpu_core=64
temperature=$1
dir_name="MD_${temperature}K_relax"

mkdir -p $dir_name
sed "s/currtemp/${temperature}/g" in.relax_bulk > ${dir_name}/in.relax_bulk
cd $dir_name
nohup mpirun -np $cpu_core ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.relax_bulk > STDOUT &
ps aux | grep mpirun


