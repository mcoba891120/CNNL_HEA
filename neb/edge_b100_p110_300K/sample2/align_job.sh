#!/bin/bash
#SBATCH --account=MST114385           # (-A) iService Project ID
#SBATCH --job-name=edge_b100_p110_300K_align_mpi          # (-J) Job name
#SBATCH --partition=ct112             # (-p) Slurm partition
#SBATCH --nodes=1                     # (-N) Maximum number of nodes to be allocated
#SBATCH --cpus-per-task=1             # (-c) Number of cores per MPI task
#SBATCH --ntasks-per-node=112         # Maximum number of tasks on each node
#SBATCH --output=align-%j.out           # (-o) Path to the standard output file
#SBATCH --error=align-%j.err            # (-e) Path to the standard error file

module purge
module load intel/2023_2

mpiexec -np 112 python align_mpi.py
