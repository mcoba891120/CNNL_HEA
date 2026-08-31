from mpi4py import MPI
from lammps import PyLammps
import numpy as np
import random
import os
from ovito.io import import_file, export_file
from ovito.modifiers import AtomicStrainModifier, SelectTypeModifier, HistogramModifier
from scipy.stats import norm  # Importing the normal distribution

def ovito_strain_sum(import_path, reference_path, particle_type=None):
    # Import the atomic configuration and reference configuration
    pipeline = import_file(import_path)
    reference_pipeline = import_file(reference_path)
    
    # Add atomic strain modifier
    atomic_strain_modifier = AtomicStrainModifier(cutoff=3.5)
    pipeline.modifiers.append(atomic_strain_modifier)
    atomic_strain_modifier.reference = reference_pipeline.source
    
    # Optionally select particles of a certain type
    if particle_type is not None:
        if particle_type not in range(1, 5):
            raise ValueError("particle_type must be between 1 and 4")
        pipeline.modifiers.append(
            SelectTypeModifier(property="Particle Type", types={particle_type})
        )
    
    # Compute the modified data
    data = pipeline.compute()
    
    # Access the shear strain data and convert it to a NumPy array
    shear_strain_array = np.array(data.particles['Shear Strain'])

    # If filtering by particle type, only sum for selected particles
    if particle_type is not None:
        selected = np.array(data.particles['Selection'])  # Binary selection array
        total_sum = shear_strain_array[selected > 0].sum()
    else:
        total_sum = shear_strain_array.sum()

    print(f"Total sum of Shear Strain: {total_sum}")
    return total_sum

def monte_carlo_simulation(num_iterations, mc_temp, lammps_data_file, reference_file, gpu_id=None):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    if rank == 0:
        print(f"Starting Monte Carlo simulation with {size} processes")
        print(f"Number of iterations: {num_iterations}")
        print(f"Temperature: {mc_temp} K")

    # Initialize list for the last 10 strain values
    last_strains = []
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
    L.pair_coeff("* * ../potentials/HEA_var3.snapcoeff ../potentials/HEA_var3.snapparam Ni Co Ti Zr")
    L.neighbor("1.0 bin")
    L.neigh_modify("every 1 delay 0 check yes")
    L.minimize("0.0 0.02 5000 10000")

    if rank == 0:
        print("Initialized LAMMPS and performed initial minimization")

    L.write_data("mc_last.data")

    strain_start = ovito_strain_sum(lammps_data_file, reference_file)
    strain_min = strain_start
    strain_last = strain_start
    last_strains.append(strain_start)

    if rank == 0:
        print(f"Initial strain: {strain_start}")

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
        e_new = L.eval("pe")
        strain_new = ovito_strain_sum("current_state.data", reference_file)

        # Update the strain history (only keep last 10)
        if len(last_strains) >= 50:
            last_strains.pop(0)
        last_strains.append(strain_new)

        # Calculate mean and std deviation from the last 10 strains
        mean_last_10 = np.mean(last_strains)
        std_last_10 = np.std(last_strains)

        # Use normal distribution to calculate acceptance probability
        probability = norm.cdf(strain_new, loc=mean_last_10, scale=std_last_10)
        print("Probability_origin= ",probability)
        probability = probability * probability_index
        print("Probability= ",probability)
        curr_rand2 = random.random()

        accept = False
        if strain_new <= strain_min:
            strain_min = strain_new
            L.write_data("strain_min.data")
            accept = True
            reason = "Accept1"
        elif strain_new <= strain_last:
            accept = True
            reason = "Accept2"
        elif curr_rand2 < probability:
            accept = True
            reason = "Accept3"
        else:
            reason = "Decline"

        if rank == 0:
            with open("MC_record.txt", "a") as f:
                f.write(f"{iter} {e_new} {strain_new} {strain_min} {reason} type_{type1}-{type2}\n")

        if accept:
            if rank == 0:
                print("Accept")
            naccept += 1
            strain_last = strain_new
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
        print(f"MC stats:\n  starting strain = {strain_start}\n  minimum strain = {strain_min}\n  accepted MC moves = {total_naccept}")

if __name__ == "__main__":
    os.environ['OMPI_MCA_opal_cuda_support'] = 'true'
    os.environ['UCX_MEMTYPE_CACHE'] = 'n'

    gpu_id = 0
    monte_carlo_simulation(num_iterations=500000, mc_temp=300, gpu_id=gpu_id, 
                           lammps_data_file="relaxation/NiCoTiZrHf_110/var3_9000_300k/after_relax.data",
                           reference_file="relaxation/NiCoTiZrHf_110/var3_9000_300k/atomic_strain_ref.data")
