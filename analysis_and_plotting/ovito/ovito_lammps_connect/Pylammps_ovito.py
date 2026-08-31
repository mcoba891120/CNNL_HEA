from ovito_strain_func import ovito_strain_sum
from ovito_stress_func import ovito_stress_sum

import os
import random
import math
from lammps import PyLammps

def monte_carlo_simulation(num_iterations, mc_temp, lammps_data_file, gpu_id):
    kT = mc_temp * 8.617333E-5
    naccept = 0
    count_output = 100

    # Initial setup
    os.makedirs('mc_folder', exist_ok=True)
    os.chdir('mc_folder')

    # Initialize LAMMPS
    L = PyLammps()
    
    # Run initial LAMMPS commands
    L.units("metal")
    L.atom_style("atomic")
    L.read_data(lammps_data_file)
    
    # GPU-specific commands
    L.package(f"gpu 1 {gpu_id}")  # Enable GPU package, using 1 GPU with specified ID
    L.suffix("gpu")     # Use GPU-enabled styles

    L.pair_style("snap")
    L.pair_coeff("* * ../../../potentials/HEA_var3.snapcoeff ../../../potentials/HEA_var3.snapparam Ni Co Ti Zr")
    L.neighbor("1.0 bin")
    L.neigh_modify("every 1 delay 0 check yes")
    L.minimize("0.0 0.02 5000 10000")

    # ... (rest of the code remains the same)

# Run the simulation
gpu_id = 0  # 指定要使用的 GPU ID，可以是 0 到 7 之間的任何數字
monte_carlo_simulation(num_iterations=500000, mc_temp=300, lammps_data_file="../after_relax.data", gpu_id=gpu_id)