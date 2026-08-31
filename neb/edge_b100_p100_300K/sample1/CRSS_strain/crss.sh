#!/bin/bash
#SBATCH --account=MST114385            # (-A) iService Project ID
#SBATCH --job-name=edge_b100_p100_300K_CRSS          # (-J) Job name
#SBATCH --partition=ct448       # (-p) Slurm partition
#SBATCH --nodes=2                     # (-N) Maximum number of nodes to be allocated
#SBATCH --cpus-per-task=1             # (-c) Number of cores per MPI task
#SBATCH --ntasks-per-node=112         # Maximum number of tasks on each node
#SBATCH --output=crss-%j.out           # (-o) Path to the standard output file
#SBATCH --error=crss-%j.err            # (-e) Path to the standard error file

module purge
module load intel/2023_2

for i in $(seq 17 20); do
  preid=$((i-1))
  mkdir -p "step_$i"
  cd "step_$i" || exit 1

  cp ../step_$preid/HEA_opt_edge1.data HEA_init_edge1.data
  cp ../step_$preid/HEA_opt_edge2.data HEA_init_edge2.data
  cp ../in.min1 in.min
  cp ../in.neb  in.neb

 mpiexec -np 224 /home/u6710794/lammps-stable_29Aug2024_update3/src/lmp_intel_cpu_intelmpi -in in.min > STDOUT1 
 sed -n "4,4p" final.cfg > final.txt ; sed -n "10,$ p" final.cfg >> final.txt ; rm final.cfg
 mpiexec -np 220 /home/u6710794/lammps-stable_29Aug2024_update3/src/lmp_intel_cpu_intelmpi -partition 10x22 -in in.neb > STDOUT2
 cd ../
done
