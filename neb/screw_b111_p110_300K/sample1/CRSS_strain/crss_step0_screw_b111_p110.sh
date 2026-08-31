#!/bin/bash
mkdir -p "step_0"
cd "step_0" || exit 1
cp ../in.min0 in.min
cp ../in.neb  in.neb

mpirun -np 63 /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_g++_openmpi -in in.min > STDOUT1
sed -n "4,4p" final.cfg > final.txt ; sed -n "10,$ p" final.cfg >> final.txt ; rm final.cfg
mpirun -np 63 /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_g++_openmpi -partition 7x9 -in in.neb > STDOUT2