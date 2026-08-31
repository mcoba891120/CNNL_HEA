import os
import numpy as np
import matplotlib.pyplot as plt
import glob
import re

def extract_avg_and_std(file_path):
    """Extract the average and standard deviation of shear strain from a data file."""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Skip header lines
        data_lines = [line for line in lines if not line.startswith('#')]
        
        # Extract strain values and counts
        strains = []
        counts = []
        for line in data_lines:
            if line.strip():  # Skip empty lines
                parts = line.strip().split()
                if len(parts) >= 2:
                    strain = float(parts[0])
                    count = float(parts[1])
                    # Add the strain value 'count' times to the list
                    strains.extend([strain] * int(count))
        
        # Calculate average and standard deviation
        if strains:
            avg = np.mean(strains)
            std = np.std(strains)
            return avg, std
        else:
            return 0, 0
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0, 0

def extract_mc_temp(dir_name):
    """Extract MC temperature from directory name."""
    # Check for MC temperature pattern
    mc_match = re.search(r'_mc(\d+)k', dir_name.lower())
    if mc_match:
        return f"mc{mc_match.group(1)}k"
    
    # If there's no MC pattern but has temperature and slip system, it's random
    relax_temp_match = re.search(r'_(\d+)k_', dir_name.lower())
    slip_system_match = re.search(r'b\d+p\d+', dir_name.lower())
    
    if relax_temp_match and slip_system_match and not re.search(r'_mc', dir_name.lower()):
        return "random"
        
    return "unknown"

def extract_relax_temp(dir_name):
    """Extract relaxation temperature from directory name."""
    # Look for temperature pattern
    temp_match = re.search(r'_(\d+)k_', dir_name.lower())
    if temp_match:
        return f"{temp_match.group(1)}k"
    return "unknown"

def extract_slip_system(dir_name):
    """Extract slip system from directory name."""
    if 'b100p110' in dir_name.lower():
        return 'b100p110'
    elif 'b111p110' in dir_name.lower():
        return 'b111p110'
    return "unknown"

def process_version_data(version_dir):
    """Process all strain data in the version directory and generate plots."""
    # Group directories by relaxation temperature, slip system, and MC temperature
    grouped_dirs = {}  # Will be {relax_temp: {slip_system: {mc_temp: [dirs]}}}
    
    # Find all subdirectories
    for subdir in glob.glob(os.path.join(version_dir, "*")):
        if os.path.isdir(subdir):
            dir_name = os.path.basename(subdir)
            
            # Extract key information
            relax_temp = extract_relax_temp(dir_name)
            slip_system = extract_slip_system(dir_name)
            mc_temp = extract_mc_temp(dir_name)
            
            # Skip if we couldn't extract necessary info
            if relax_temp == "unknown" or slip_system == "unknown" or mc_temp == "unknown":
                print(f"Skipping directory with unrecognized format: {dir_name}")
                continue
            
            # Print extracted information for debugging
            print(f"Directory: {dir_name}")
            print(f"  Relax Temp: {relax_temp}")
            print(f"  Slip System: {slip_system}")
            print(f"  MC Temp: {mc_temp}")
            
            # Initialize nested dictionaries if needed
            if relax_temp not in grouped_dirs:
                grouped_dirs[relax_temp] = {}
            if slip_system not in grouped_dirs[relax_temp]:
                grouped_dirs[relax_temp][slip_system] = {}
            if mc_temp not in grouped_dirs[relax_temp][slip_system]:
                grouped_dirs[relax_temp][slip_system][mc_temp] = []
            
            # Add directory to appropriate group
            grouped_dirs[relax_temp][slip_system][mc_temp].append(subdir)
    
    # Process each group and create plots
    for relax_temp in grouped_dirs:
        for slip_system in grouped_dirs[relax_temp]:
            # Collect all directories for this relax_temp and slip_system
            mc_temp_dirs = grouped_dirs[relax_temp][slip_system]
            create_strain_plot(mc_temp_dirs, relax_temp, slip_system, version_dir)

def create_strain_plot(mc_temp_dirs, relax_temp, slip_system, version_dir):
    """Create a strain plot for a specific relaxation temperature and slip system."""
    elements = ['Co', 'Ni', 'Ti', 'Zr', 'Hf']
    
    # Define data types and their colors/labels
    data_types = ['random', 'mc300k', 'mc1273k']
    data_type_colors = {
        'random': 'black',
        'mc300k': 'cyan',
        'mc1273k': 'red'
    }
    data_type_labels = {
        'random': 'Random',
        'mc300k': 'MC 300K',
        'mc1273k': 'MC 1273K'
    }
    
    # Create plot
    plt.figure(figsize=(8, 6))
    x_positions = np.arange(len(elements))
    width = 0.2  # Width of the bars
    
    # First collect all data
    all_data = {}  # Will store {data_type: {element: [(avg, std), ...]}}
    
    # Initialize data structure
    for data_type in data_types:
        all_data[data_type] = {}
        for element in elements:
            all_data[data_type][element] = []
    
    # Collect data from each directory
    for mc_temp, directories in mc_temp_dirs.items():
        for directory in directories:
            for element_idx, element in enumerate(elements):
                strain_file = os.path.join(directory, f"{element}_strain.txt")
                if os.path.exists(strain_file):
                    avg, std = extract_avg_and_std(strain_file)
                    # Only collect data for the defined data types
                    if mc_temp in data_types:
                        all_data[mc_temp][element].append((avg, std))
    
    # Plot data for each data type and element
    offsets = {data_types[i]: (i-1)*width for i in range(len(data_types))}
    
    for data_type in data_types:
        for element_idx, element in enumerate(elements):
            data_points = all_data[data_type][element]
            if data_points:
                avgs = [d[0] for d in data_points]
                stds = [d[1] for d in data_points]
                avg = np.mean(avgs)
                std = np.mean(stds)
                
                x_pos = element_idx + offsets[data_type]
                plt.errorbar(x_pos, avg, yerr=std, fmt='o', color=data_type_colors[data_type], 
                            label=data_type_labels[data_type] if element_idx == 0 else "")
    
    # Set plot properties
    plt.xticks(x_positions, elements)
    plt.xlabel('Elements')
    plt.ylabel('Shear Strain')
    plt.title(f'Shear Strain by Element ({relax_temp}, {slip_system})')
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Save plot
    output_path = os.path.join(version_dir, f"strain_plot_{relax_temp}_{slip_system}.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Plot saved to: {output_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python plot_strain_data.py version_directory")
        sys.exit(1)
    
    version_dir = sys.argv[1]
    if not os.path.isdir(version_dir):
        print(f"Error: Directory '{version_dir}' does not exist.")
        sys.exit(1)
    
    process_version_data(version_dir)
    print("Plotting complete!")