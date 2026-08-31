#!/bin/bash
#SBATCH --account=MST113465           # (-A) iService Project ID
#SBATCH --job-name=NEB111110          # (-J) Job name
#SBATCH --partition=ct448             # (-p) Slurm partition
#SBATCH --nodes=2                     # (-N) Maximum number of nodes to be allocated
#SBATCH --cpus-per-task=1             # (-c) Number of cores per MPI task
#SBATCH --ntasks-per-node=112         # Maximum number of tasks on each node
#SBATCH --output=job-%j.out           # (-o) Path to the standard output file
#SBATCH --error=job-%j.err            # (-e) Path to the standard error file

module purge
module load intel/2023_2

mkdir step_0
cd step_0/
cp ../in.min0 in.min
cp ../in.neb in.neb
mpiexec -np 224 /home/pyyang0519/lammps-stable_29Aug2024_update3/src/lmp_intel_cpu_intelmpi -in in.min > STDOUT1
sed -n "4,4p" final.cfg > final.txt ; sed -n "10,$ p" final.cfg >> final.txt ; rm final.cfg
mpiexec -np 220 /home/pyyang0519/lammps-stable_29Aug2024_update3/src/lmp_intel_cpu_intelmpi -partition 10x22 -in in.neb > STDOUT2
cd ../

for i in $(seq 1 5)
do
	preid=$(($i-1))
	mkdir step_$i
	cd step_$i
	cp ../step_$preid/HEA_opt_edge1.data HEA_init_edge1.data
	cp ../step_$preid/HEA_opt_edge2.data HEA_init_edge2.data
	cp ../in.min1 in.min
	cp ../in.neb in.neb
	mpiexec -np 224 /home/pyyang0519/lammps-stable_29Aug2024_update3/src/lmp_intel_cpu_intelmpi -in in.min > STDOUT1
	sed -n "4,4p" final.cfg > final.txt ; sed -n "10,$ p" final.cfg >> final.txt ; rm final.cfg
	mpiexec -np 220 /home/pyyang0519/lammps-stable_29Aug2024_update3/src/lmp_intel_cpu_intelmpi -partition 10x22 -in in.neb > STDOUT2
	cd ../
done

