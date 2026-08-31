#!/bin/bash
#SBATCH --account=MST114385
#SBATCH --job-name=neb_b100_p100_300K_sample1
#SBATCH --partition=ct448
#SBATCH --nodes=2
#SBATCH --cpus-per-task=1
#SBATCH --ntasks-per-node=63
#SBATCH --output=neb.out
#SBATCH --error=neb.err

module purge
module load intel/2023_2

mpiexec -np 126 /home/u6710794/lammps-stable_29Aug2024_update3/src/lmp_intel_cpu_intelmpi -partition 21x6 -in in.neb > STDOUT_neb
