#!/bin/bash
#SBATCH --account=MST113465           # (-A) iService Project ID
#SBATCH --job-name=S100100            # (-J) Job name
#SBATCH --partition=development       # (-p) Slurm partition
#SBATCH --nodes=1                     # (-N) Maximum number of nodes to be allocated
#SBATCH --cpus-per-task=1             # (-c) Number of cores per MPI task
#SBATCH --ntasks-per-node=112         # Maximum number of tasks on each node
#SBATCH --output=job-%j.out           # (-o) Path to the standard output file
#SBATCH --error=job-%j.err            # (-e) Path to the standard error file

module purge
module load intel/2023_2

mpiexec -np 112 /home/pyyang0519/lammps-stable_29Aug2024_update3/src/lmp_intel_cpu_intelmpi -in in.min > STDOUT
