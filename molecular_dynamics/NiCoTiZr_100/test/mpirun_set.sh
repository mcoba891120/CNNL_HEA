#!/bin/bash

nohup mpirun -np 128 /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.relax.NiCoTiZr > STDOUT &

ps -u | grep mpirun
