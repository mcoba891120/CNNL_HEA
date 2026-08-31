#!/bin/bash

input_file="POSCAR_modified.data"

relax_file="after_relax_HEA.data"
lx=$(sed -n "6,6p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
ly=$(sed -n "7,7p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
lz=$(sed -n "8,8p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')

/home/jhenyu/lammps-stable_2Aug2023_update2/src/lmp_g++_openmpi -var input_file $input_file -var newlx $lx -var newly $ly -var newlz $lz -in in.reshape
