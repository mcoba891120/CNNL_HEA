#!/bin/bash
#PBS -l nodes=1:ppn=63
#PBS -N CRSS_edge_b100_p100_300K_step0
#PBS -q amd

export PATH=/home/cnnltmp01/package/cuda-12.4/bin:$PATH
export LD_LIBRARY_PATH=/home/cnnltmp01/package/cuda-12.4/lib64:$LD_LIBRARY_PATH
export PATH=/home/cnnltmp01/ucx-1.17.0/bin:$PATH
export LD_LIBRARY_PATH=/home/cnnltmp01/ucx-1.17.0/lib:$LD_LIBRARY_PATH
export PATH=/home/cnnltmp01/package/openmpi-4.1.6/bin:$PATH
export LD_LIBRARY_PATH=/home/cnnltmp01/package/openmpi-4.1.6/lib:$LD_LIBRARY_PATH

cd $PBS_O_WORKDIR
mkdir -p "step_0"
cd "step_0" || exit 1
cp ../in.min0 in.min
cp ../in.neb  in.neb

mpirun -hostfile $PBS_NODEFILE -np 63 /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_g++_openmpi -in in.min > STDOUT1
sed -n "4,4p" final.cfg > final.txt ; sed -n "10,$ p" final.cfg >> final.txt ; rm final.cfg
mpirun -hostfile $PBS_NODEFILE -np 63 /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_g++_openmpi -partition 7x9 -in in.neb > STDOUT2