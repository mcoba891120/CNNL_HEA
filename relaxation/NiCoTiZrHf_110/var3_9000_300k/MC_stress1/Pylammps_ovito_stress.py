from mpi4py import MPI
from lammps import PyLammps
import numpy as np
import random
import os
from ovito.io import import_file, export_file
from ovito.modifiers import AtomicStrainModifier, SelectTypeModifier, HistogramModifier
from scipy.stats import norm  # Importing the normal distribution

def sum_stress_in_lammps(L):
    # Extract the stress array directly from LAMMPS
    stress_array = L.lmp.extract_variable("sa_von", "all", 1)
    
    # Ensure it's a valid array and sum it up
    if stress_array is not None:
        stress_sum = np.sum(stress_array)
        print(f"Total sum of Shear Stress: {stress_sum}")
        return stress_sum
    else:
        raise ValueError("Failed to extract stress data from LAMMPS.")

def monte_carlo_simulation(num_iterations, mc_temp, lammps_data_file, gpu_id=None):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    if rank == 0:
        print(f"Starting Monte Carlo simulation with {size} processes")
        print(f"Number of iterations: {num_iterations}")
        print(f"Temperature: {mc_temp} K")

    # Initialize list for the last 10 stress values
    last_stresss = []
    naccept = 0
    probability_index = 0.1
    count_output = 100
    count_increment = 100

    if rank == 0:
        os.makedirs('mc_folder', exist_ok=True)
        os.chdir('mc_folder')
        print("Created mc_folder and changed directory")

    # Initialize LAMMPS
    L = PyLammps(cmdargs=["-k", "on", "g", "1", "-sf", "kk", "-pk", "kokkos", "newton", "on", "neigh", "half"])
    L.units("metal")
    L.atom_style("atomic")
    L.read_data(lammps_data_file)
    L.pair_style("snap")
    L.pair_coeff("* * ../../../../potentials/HEA_var3.snapcoeff ../../../../potentials/HEA_var3.snapparam Ni Co Ti Zr")
    L.neighbor("1.0 bin")
    L.neigh_modify("every 1 delay 0 check yes")
    L.command("compute sta all stress/atom NULL")
    L.command("variable vol equal vol")
    L.command("variable natoms equal count(all)")
    L.command("variable va atom v_vol/v_natoms")
    L.command("variable sa_xx atom 1E-4*c_sta[1]/v_va")
    L.command("variable sa_yy atom 1E-4*c_sta[2]/v_va")
    L.command("variable sa_zz atom 1E-4*c_sta[3]/v_va")
    L.command("variable sa_xy atom 1E-4*c_sta[4]/v_va")
    L.command("variable sa_xz atom 1E-4*c_sta[5]/v_va")
    L.command("variable sa_yz atom 1E-4*c_sta[6]/v_va")
    L.command("variable sa_hydro atom (v_sa_xx+v_sa_yy+v_sa_zz)/3.0")
    L.command("variable sa_von atom sqrt(0.5*((v_sa_xx-v_sa_yy)^2+(v_sa_yy-v_sa_zz)^2+(v_sa_zz-v_sa_xx)^2)+3.0*((v_sa_xy)^2+(v_sa_xz)^2+(v_sa_yz)^2))")
    L.minimize("0.0 0.02 5000 10000")

    if rank == 0:
        print("Initialized LAMMPS and performed initial minimization")

    L.write_data("mc_last.data")
    
    # Calculate initial stress directly from LAMMPS data
    stress_start = sum_stress_in_lammps(L)
    stress_min = stress_start
    stress_last = stress_start
    last_stresss.append(stress_start)

    if rank == 0:
        print(f"Initial stress: {stress_start}")

    for iter in range(1, num_iterations + 1):
        if rank == 0 and iter % 100 == 0:
            print(f"Iteration {iter}")

        # Choose random swap type
        swap_types = [(1, 2), (3, 4)]
        type1, type2 = random.choice(swap_types)

        # Perform atom swap
        L.reset_timestep(0)
        L.fix(f"1 all atom/swap 1 1 {random.randint(10000000, 99999999)} 100000000 types {type1} {type2} ke no")
        L.run(1, "post no")
        L.unfix(1)
        L.minimize("0.0 0.02 5000 10000")
        L.run(0)
        L.write_data("current_state.data")
        
        # Calculate new stress after relaxation
        e_new = L.eval("pe")
        stress_new = sum_stress_in_lammps(L)

        # Update the stress history (only keep last 10)
        if len(last_stresss) >= 50:
            last_stresss.pop(0)
        last_stresss.append(stress_new)

        # Calculate mean and std deviation from the last 10 stresses
        mean_last_10 = np.mean(last_stresss)
        std_last_10 = np.std(last_stresss)

        # Use normal distribution to calculate acceptance probability
        probability = norm.cdf(stress_new, loc=mean_last_10, scale=std_last_10)
        probability = probability * probability_index
        curr_rand2 = random.random()

        accept = False
        if stress_new <= stress_min:
            stress_min = stress_new
            L.write_data("stress_min.data")
            accept = True
            reason = "Accept1"
        elif stress_new <= stress_last:
            accept = True
            reason = "Accept2"
        elif curr_rand2 < probability:
            accept = True
            reason = "Accept3"
            print("Probability= ", probability)
        else:
            reason = "Decline"

        if rank == 0:
            with open("MC_record.txt", "a") as f:
                f.write(f"{iter} {e_new} {stress_new} {stress_min} {reason} type_{type1}-{type2}\n")

        if accept:
            if rank == 0:
                print("Accept")
            naccept += 1
            stress_last = stress_new
            L.write_data("mc_last.data")
            if iter == count_output:
                L.write_data(f"mc_loop_{iter}.data")
        else:
            if rank == 0:
                print("Decline")
            # Revert to previous state
            L.delete_atoms("group all")
            L.read_data("mc_last.data", "add append")

        if iter == count_output:
            count_output += count_increment
            if rank == 0:
                print(f"Saved state at iteration {iter}")

        acceptance_rate = naccept / iter
        if rank == 0:
            print(f"Acceptance rate after iteration {iter}: {acceptance_rate}") 

        comm.Barrier()

    total_naccept = comm.reduce(naccept, op=MPI.SUM, root=0)

    if rank == 0:
        print(f"MC stats:\n  starting stress = {stress_start}\n  minimum stress = {stress_min}\n  accepted MC moves = {total_naccept}")

if __name__ == "__main__":
    os.environ['OMPI_MCA_opal_cuda_support'] = 'true'
    os.environ['UCX_MEMTYPE_CACHE'] = 'n'

    gpu_id = 0
    monte_carlo_simulation(num_iterations=500000, mc_temp=300, gpu_id=gpu_id,
                           lammps_data_file="relaxation/NiCoTiZrHf_110/var3_9000_300k/after_relax.data")
