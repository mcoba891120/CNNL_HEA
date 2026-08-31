#!/bin/bash
#PBS -l nodes=1:ppn=63
#PBS -N CRSSsb111p110_300K
#PBS -q amd

export PATH=/home/cnnltmp01/package/cuda-12.4/bin:$PATH
export LD_LIBRARY_PATH=/home/cnnltmp01/package/cuda-12.4/lib64:$LD_LIBRARY_PATH
export PATH=/home/cnnltmp01/ucx-1.17.0/bin:$PATH
export LD_LIBRARY_PATH=/home/cnnltmp01/ucx-1.17.0/lib:$LD_LIBRARY_PATH
export PATH=/home/cnnltmp01/package/openmpi-4.1.6/bin:$PATH
export LD_LIBRARY_PATH=/home/cnnltmp01/package/openmpi-4.1.6/lib:$LD_LIBRARY_PATH

cd $PBS_O_WORKDIR
for i in $(seq 1 20); do
  preid=$((i-1))
  mkdir -p "step_$i"
  cd "step_$i" || exit 1

  cp ../step_$preid/HEA_opt_edge1.data HEA_init_edge1.data
  cp ../step_$preid/HEA_opt_edge2.data HEA_init_edge2.data
  cp ../in.min1 in.min
  cp ../in.neb  in.neb

 mpirun -hostfile $PBS_NODEFILE -np 63 /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_g++_openmpi -in in.min > STDOUT1
 sed -n "4,4p" final.cfg > final.txt ; sed -n "10,$ p" final.cfg >> final.txt ; rm final.cfg
 mpirun -hostfile $PBS_NODEFILE -np 63 /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_g++_openmpi -partition 7x9 -in in.neb > STDOUT2
 cd ../
done