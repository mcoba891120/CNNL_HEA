#!/bin/bash

input_file="HEA_init_screw.data"
relax_mode="md"
current_path=$(pwd)
cpu_core=64

mkdir -p ${relax_mode}_300K_slip
relax_file="MD_300K_relax/after_relax_bulk.data"
lx=$(sed -n "6,6p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
ly=$(sed -n "7,7p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
lz=$(sed -n "8,8p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')

mpirun -np 1 /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -var input_file $input_file -var newlx $lx -var newly $ly -var newlz $lz -in in.build_slab
#/ceph/work/CNNL/package/lammps-stable_2Aug2023_update3/src/lmp_g++_openmpi -var input_file $input_file -var newlx $lx -var newly $ly -var newlz $lz -in in.build_slab
mv tmp_slab.data ${relax_mode}_300K_slip/init_slab.data
sed  "s/currtemp/300/g" in.relax_slab > ${relax_mode}_300K_slip/in.relax_slab
cd ${relax_mode}_300K_slip
nohup mpirun -np $cpu_core ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.relax_slab > STDOUT &
ps aux | grep mpirun
# sed  "s/currtemp/300/g" in.slip > ${relax_mode}_300K_slip/in.slip

# cd $current_path
# mkdir -p ${relax_mode}_1273K_slip
# relax_file="MD_1273K_relax/after_relax_bulk.data"
# lx=$(sed -n "6,6p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
# ly=$(sed -n "7,7p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
# lz=$(sed -n "8,8p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')

# mpirun -np 1 /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -var input_file $input_file -var newlx $lx -var newly $ly -var newlz $lz -in in.build_slab
# #/ceph/work/CNNL/package/lammps-stable_2Aug2023_update3/src/lmp_g++_openmpi -var input_file $input_file -var newlx $lx -var newly $ly -var newlz $lz -in in.build_slab
# mv tmp_slab.data ${relax_mode}_1273K_slip/init_slab.data
# sed  "s/currtemp/1273/g" in.relax_slab > ${relax_mode}_1273K_slip/in.relax_slab
# cd ${relax_mode}_1273K_slip
# nohup mpirun -np $cpu_core ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.relax_slab > STDOUT &
# ps aux | grep mpirun

# sed  "s/currtemp/1273/g" in.slip > ${relax_mode}_1273K_slip/in.slip
