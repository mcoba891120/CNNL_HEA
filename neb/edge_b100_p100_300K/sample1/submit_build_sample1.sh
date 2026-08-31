#!/bin/bash
#SBATCH --account=MST114385
#SBATCH --job-name=build_sample1
#SBATCH --partition=ct112
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --ntasks-per-node=1
#SBATCH --output=job-%j.out
#SBATCH --error=job-%j.err

module purge
module load intel/2023_2

mpiexec -np 1 /home/u6710794/lammps-stable_29Aug2024_update3/src/lmp_intel_cpu_intelmpi -in in.build_edge > STDOUT_build
