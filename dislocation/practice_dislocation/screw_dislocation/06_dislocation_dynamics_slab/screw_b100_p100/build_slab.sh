#!/bin/bash

input_file="HEA_init_screw.data"

mkdir -p tfMC_300K_slip
relax_file="MD_300K_relax/after_relax_bulk.data"
lx=$(sed -n "6,6p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
ly=$(sed -n "7,7p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
lz=$(sed -n "8,8p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')

/home/pyyang/lammps-stable_2Aug2023/src/lmp_kokkos_cuda_mpi_a100 -var input_file $input_file -var newlx $lx -var newly $ly -var newlz $lz -in in.build_slab
#/ceph/work/CNNL/package/lammps-stable_2Aug2023_update3/src/lmp_g++_openmpi -var input_file $input_file -var newlx $lx -var newly $ly -var newlz $lz -in in.build_slab
mv tmp_slab.data tfMC_300K_slip/init_slab.data
sed  "s/currtemp/300/g" in.relax_slab > tfMC_300K_slip/in.relax_slab

mkdir -p tfMC_1273K_slip
relax_file="MD_1273K_relax/after_relax_bulk.data"
lx=$(sed -n "6,6p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
ly=$(sed -n "7,7p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
lz=$(sed -n "8,8p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')

/home/pyyang/lammps-stable_2Aug2023/src/lmp_kokkos_cuda_mpi_a100 -var input_file $input_file -var newlx $lx -var newly $ly -var newlz $lz -in in.build_slab
#/ceph/work/CNNL/package/lammps-stable_2Aug2023_update3/src/lmp_g++_openmpi -var input_file $input_file -var newlx $lx -var newly $ly -var newlz $lz -in in.build_slab
mv tmp_slab.data tfMC_1273K_slip/init_slab.data
sed  "s/currtemp/1273/g" in.relax_slab > tfMC_1273K_slip/in.relax_slab

