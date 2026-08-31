#!/bin/bash
#SBATCH --account=MST114385           # (-A) iService Project ID
#SBATCH --job-name=screw_b100_p100_300K_neb_sample2          # (-J) Job name
#SBATCH --partition=ct448             # (-p) Slurm partition
#SBATCH --nodes=2                     # (-N) Maximum number of nodes to be allocated
#SBATCH --cpus-per-task=1             # (-c) Number of cores per MPI task
#SBATCH --ntasks-per-node=105         # Maximum number of tasks on each node
#SBATCH --output=neb-%j.out           # (-o) Path to the standard output file
#SBATCH --error=neb-%j.err            # (-e) Path to the standard error file

module purge
module load intel/2023_2

mpiexec -np 210 /home/u6710794/lammps-stable_29Aug2024_update3/src/lmp_intel_cpu_intelmpi -partition 21x10 -in in.neb > STDOUT2
