import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress

def calculate_youngs_modulus(file_path):
    data = np.loadtxt(file_path, skiprows=1)
    strain = data[:, 0]
    stress = data[:, 1]  # Using stress in x direction
    slope, _, _, _, _ = linregress(strain, stress)  # Using first 20 points for linear region
    return slope

def extract_info_from_path(path):
    parts = path.split(os.path.sep)
    alloy_orientation = parts[-3]
    
    # Handle cases where alloy and orientation might be combined
    if '_' in alloy_orientation:
        alloy, orientation = alloy_orientation.split('_', 1)
    else:
        alloy = alloy_orientation
        orientation = 'unknown'
    
    var_temp_part = parts[-2]
    var_parts = var_temp_part.split('_')
    
    if len(var_parts) == 3:
        var_num, total_atoms, temperature = var_parts
    elif len(var_parts) == 2:
        var_num, temperature = var_parts
        total_atoms = 'unknown'
    else:
        print(f"Unexpected format in {var_temp_part}")
        return None
    
    temperature = int(temperature[:-1])  # Remove 'k' and convert to int
    return alloy, orientation, temperature, var_num, total_atoms

def plot_youngs_modulus_vs_temperature(base_path):
    data = {}
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.startswith("SS_curve") and file.endswith(".txt"):
                file_path = os.path.join(root, file)
                info = extract_info_from_path(file_path)
                if info is None:
                    continue
                alloy, orientation, temperature, var_num, total_atoms = info
                youngs_modulus = calculate_youngs_modulus(file_path)
                
                key = (alloy, orientation, var_num, total_atoms)
                if key not in data:
                    data[key] = []
                data[key].append((temperature, youngs_modulus))

    # Plotting
    orientations = set(key[1] for key in data.keys())
    alloys = set(key[0] for key in data.keys())
    
    for orientation in orientations:
        plt.figure(figsize=(10, 6))
        for alloy in alloys:
            for key, values in data.items():
                if key[0] == alloy and key[1] == orientation:
                    temperatures, moduli = zip(*sorted(values))
                    label = f"{alloy} - {key[2]} - {key[3]} atoms"
                    plt.plot(temperatures, moduli, marker='o', label=label)
        
        plt.xlabel('Temperature (K)')
        plt.ylabel("Young's Modulus (GPa)")
        plt.title(f"Young's Modulus vs Temperature - Orientation {orientation}")
        plt.legend()
        plt.grid(True)
        plt.savefig(f"youngs_modulus_vs_temp_orientation_{orientation}.png")
        plt.close()

# Usage
base_path = "./compress"
plot_youngs_modulus_vs_temperature(base_path)