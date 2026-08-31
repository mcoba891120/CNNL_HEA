#!/bin/bash
#PBS -N neb_snap_edge_b100_p100_300K_sample1_next_1
#PBS -q amd
#PBS -l nodes=1:ppn=63

set -euo pipefail

cd "$PBS_O_WORKDIR"

# === 你的環境 ===
export PATH=/home/cnnltmp01/package/cuda-12.4/bin:$PATH
export LD_LIBRARY_PATH=/home/cnnltmp01/package/cuda-12.4/lib64:$LD_LIBRARY_PATH
export PATH=/home/cnnltmp01/ucx-1.17.0/bin:$PATH
export LD_LIBRARY_PATH=/home/cnnltmp01/ucx-1.17.0/lib:$LD_LIBRARY_PATH
export PATH=/home/cnnltmp01/package/openmpi-4.1.6/bin:$PATH
export LD_LIBRARY_PATH=/home/cnnltmp01/package/openmpi-4.1.6/lib:$LD_LIBRARY_PATH

# === 執行（28 ranks，NEB 7x4）===
MPIRUN=mpirun
LMP=/home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_g++_openmpi

# 直接跑你目錄裡的 in.neb（LAMMPS 輸入檔）
$MPIRUN -hostfile "$PBS_NODEFILE" -np 63 \
  "$LMP" -partition 7x9 -in in.neb > STDOUT_neb
