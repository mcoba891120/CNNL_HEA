#!/bin/bash

current_path=$(pwd)
cpu_core=64
mkdir -p MD_300K_relax
sed  "s/currtemp/300/g" in.relax_bulk > MD_300K_relax/in.relax_bulk
cd MD_300K_relax
nohup mpirun -np $cpu_core ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.relax_bulk > STDOUT &
ps aux | grep mpirun

cd $current_path
mkdir -p MD_1273K_relax
sed  "s/currtemp/1273/g" in.relax_bulk > MD_1273K_relax/in.relax_bulk
cd MD_1273K_relax
nohup mpirun -np $cpu_core ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.relax_bulk > STDOUT &
ps aux | grep mpirun

