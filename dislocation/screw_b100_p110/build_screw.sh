#!/bin/bash

mpirun -np 1 /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in in.build_screw
#/ceph/work/CNNL/package/lammps-stable_2Aug2023_update3/src/lmp_g++_openmpi -in in.build_screw
