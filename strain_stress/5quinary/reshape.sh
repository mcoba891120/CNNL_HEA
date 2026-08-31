#!/bin/bash

input_file=$1
relax_file=$2
output_dir=$(dirname "$3")

lx=$(sed -n "6,6p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
ly=$(sed -n "7,7p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
lz=$(sed -n "8,8p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')

cd $output_dir
mpirun -np 1 ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -var input_file $input_file -var newlx $lx -var newly $ly -var newlz $lz -in ../in.reshape