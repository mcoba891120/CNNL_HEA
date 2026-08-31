#!/bin/bash

input_file="HEA_init_screw.data"

# tfMC_300K_slip
mkdir -p tfMC_300K_slip
relax_file="MD_300K_relax/after_relax_bulk.data"

lx=$(sed -n "6,6p" $relax_file | awk '{print $2}' | awk '{printf("%f",$0)}')
ly=$(sed -n "7,7p" $relax_file | awk '{print $2}' | awk '{printf("%f",$0)}')
lz=$(sed -n "8,8p" $relax_file | awk '{print $2}' | awk '{printf("%f",$0)}')

newlx=$(echo "$lx * 3.0" | bc -l)
newly=$ly
newlz=$(echo "$lz * 3.0" | bc -l)

# LAMMPS Command
/home/jhenyu/lammps-stable_2Aug2023_update2/src/lmp_g++_openmpi \
    -var input_file $input_file \
    -var newlx $newlx \
    -var newly $newly \
    -var newlz $newlz \
    -in in.build_slab

cp tmp_slab.data tfMC_300K_slip/init_slab.data
sed "s/currtemp/300/g" in.relax_slab_manual > tfMC_300K_slip/in.relax_slab_manual

# tfMC_1273K_slip
mkdir -p tfMC_1273K_slip
relax_file="MD_1273K_relax/after_relax_bulk.data"

lx=$(sed -n "6,6p" $relax_file | awk '{print $2}' | awk '{printf("%f",$0)}')
ly=$(sed -n "7,7p" $relax_file | awk '{print $2}' | awk '{printf("%f",$0)}')
lz=$(sed -n "8,8p" $relax_file | awk '{print $2}' | awk '{printf("%f",$0)}')

newlx=$(echo "$lx * 3.0" | bc -l)
newly=$ly
newlz=$(echo "$lz * 3.0" | bc -l)

# LAMMPS Command
/home/jhenyu/lammps-stable_2Aug2023_update2/src/lmp_g++_openmpi \
    -var input_file $input_file \
    -var newlx $newlx \
    -var newly $newly \
    -var newlz $newlz \
    -in in.build_slab

cp tmp_slab.data tfMC_1273K_slip/init_slab.data
sed "s/currtemp/1273/g" in.relax_slab_manual > tfMC_1273K_slip/in.relax_slab_manual
# tfMC_600K_slip
#mkdir -p tfMC_600K_slip
#relax_file="MD_600K_relax/after_relax_bulk.data"

#lx=$(sed -n "6,6p" $relax_file | awk '{print $2}' | awk '{printf("%f",$0)}')
#ly=$(sed -n "7,7p" $relax_file | awk '{print $2}' | awk '{printf("%f",$0)}')
#lz=$(sed -n "8,8p" $relax_file | awk '{print $2}' | awk '{printf("%f",$0)}')

#newlx=$(echo "$lx * 3.0" | bc -l)
#newly=$ly
#newlz=$(echo "$lz * 3.0" | bc -l)

#/home/jhenyu/lammps-stable_2Aug2023_update2/src/lmp_g++_openmpi \
#    -var input_file $input_file \
#    -var newlx $newlx \
#    -var newly $newly \
#    -var newlz $newlz \
#    -in in.build_slab

#mv tmp_slab.data tfMC_600K_slip/init_slab.data
#sed "s/currtemp/600/g" in.relax_slab > tfMC_600K_slip/in.relax_slab

# tfMC_900K_slip
#mkdir -p tfMC_900K_slip
#relax_file="MD_900K_relax/after_relax_bulk.data"

#lx=$(sed -n "6,6p" $relax_file | awk '{print $2}' | awk '{printf("%f",$0)}')
#ly=$(sed -n "7,7p" $relax_file | awk '{print $2}' | awk '{printf("%f",$0)}')
#lz=$(sed -n "8,8p" $relax_file | awk '{print $2}' | awk '{printf("%f",$0)}')

#newlx=$(echo "$lx * 3.0" | bc -l)
#newly=$ly
#newlz=$(echo "$lz * 3.0" | bc -l)

#/home/jhenyu/lammps-stable_2Aug2023_update2/src/lmp_g++_openmpi \
#    -var input_file $input_file \
#    -var newlx $newlx \
#    -var newly $newly \
#    -var newlz $newlz \
#    -in in.build_slab

#mv tmp_slab.data tfMC_900K_slip/init_slab.data
#sed "s/currtemp/900/g" in.relax_slab > tfMC_900K_slip/in.relax_slab

