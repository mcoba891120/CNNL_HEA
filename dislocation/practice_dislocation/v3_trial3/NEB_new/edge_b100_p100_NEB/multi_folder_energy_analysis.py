#!/usr/bin/env python3
"""
Multi-folder Energy Analysis Script
Processes multiple folders containing screen files and generates comparative plots.
Results are saved in a dedicated output folder.
"""

import os
import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import shutil
import warnings

def discover_folders(base_path):
    """
    Automatically discover structure folders and their subfolders (pct, L..._R..., and next_).
    Returns a list of folder paths to process.
    """
    folder_paths = []
    
    print(f"Discovering folders in: {base_path}")
    print("-" * 50)
    
    # Find all structure folders (structure1, structure2, etc.)
    structure_folders = []
    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        if os.path.isdir(item_path) and item.startswith("structure"):
            structure_folders.append(item_path)
            print(f"Found structure folder: {item}")
    
    if not structure_folders:
        warnings.warn("No structure folders found in the current directory!")
        return folder_paths
    
    # Define the pct folders to look for
    pct_folders = ["12.5pct", "16.7pct", "20pct", "25pct"]
    
    # Process each structure folder
    for structure_folder in structure_folders:
        structure_name = os.path.basename(structure_folder)
        print(f"\nProcessing {structure_name}:")
        
        try:
            # Look for pct subfolders
            subfolders = os.listdir(structure_folder)
            
            for pct_folder in pct_folders:
                if pct_folder in subfolders:
                    pct_path = os.path.join(structure_folder, pct_folder)
                    print(f"  Found pct folder: {structure_name}/{pct_folder}")
                    
                    # Look for L..._R... subfolders within pct folder
                    try:
                        pct_subfolders = os.listdir(pct_path)
                        l_r_folders = [f for f in pct_subfolders if os.path.isdir(os.path.join(pct_path, f)) and f.startswith("L-") and "_R" in f]
                        
                        for l_r_folder in l_r_folders:
                            l_r_path = os.path.join(pct_path, l_r_folder)
                            folder_paths.append(l_r_path)
                            print(f"    Found L..._R... subfolder: {structure_name}/{pct_folder}/{l_r_folder}")
                            
                            # Look for next_ subfolders within L..._R... folder
                            try:
                                l_r_subfolders = os.listdir(l_r_path)
                                next_folders = [f for f in l_r_subfolders if os.path.isdir(os.path.join(l_r_path, f)) and f.startswith("next_")]
                                
                                for next_folder in next_folders:
                                    next_path = os.path.join(l_r_path, next_folder)
                                    folder_paths.append(next_path)
                                    print(f"      Found next_ subfolder: {structure_name}/{pct_folder}/{l_r_folder}/{next_folder}")
                                    
                            except PermissionError:
                                warnings.warn(f"Permission denied when accessing {l_r_path}")
                            except Exception as e:
                                warnings.warn(f"Error accessing {l_r_path}: {e}")
                            
                    except PermissionError:
                        warnings.warn(f"Permission denied when accessing {pct_path}")
                    except Exception as e:
                        warnings.warn(f"Error accessing {pct_path}: {e}")
                else:
                    print(f"  Missing pct folder: {structure_name}/{pct_folder}")
                
        except PermissionError:
            warnings.warn(f"Permission denied when accessing {structure_folder}")
        except Exception as e:
            warnings.warn(f"Error accessing {structure_folder}: {e}")
    
    print(f"\nTotal folders discovered: {len(folder_paths)}")
    return folder_paths

def extract_length_from_neb_data(neb_data_file):
    """
    Extract y-direction length from neb_1.data file.
    Returns the length value or None if not found.
    """
    try:
        with open(neb_data_file, 'r') as f:
            for line in f:
                if 'ylo yhi' in line:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        return float(parts[1])  # yhi value
        return None
    except FileNotFoundError:
        warnings.warn(f"File {neb_data_file} not found")
        return None
    except Exception as e:
        warnings.warn(f"Error reading {neb_data_file}: {e}")
        return None

def extract_energy_final(screen_file, length_factor=1.0):
    """
    Extract Energy final value from a screen file.
    Returns the energy value divided by length_factor or None if not found.
    """
    try:
        with open(screen_file, 'r') as f:
            content = f.read()
        
        # Look for the pattern: Energy initial, next-to-last, final = 
        # followed by three numbers on the next line
        pattern = r'Energy initial, next-to-last, final = \s*\n\s*([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)'
        match = re.search(pattern, content)
        
        if match:
            # Return the third value (final energy) divided by length factor
            energy = float(match.group(3))
            return energy / length_factor
        else:
            warnings.warn(f"Could not find Energy final pattern in {screen_file}")
            return None
            
    except FileNotFoundError:
        warnings.warn(f"File {screen_file} not found")
        return None
    except Exception as e:
        warnings.warn(f"Error reading {screen_file}: {e}")
        return None

def calculate_energy_barrier(energies, screen_numbers):
    """
    Calculate energy barrier from energy data.
    Energy barrier is defined as the difference between maximum and minimum energy values.
    Returns dictionary with barrier information.
    """
    if len(energies) < 2:
        return None
    
    # Convert to numpy arrays for easier calculation
    energies = np.array(energies)
    screen_numbers = np.array(screen_numbers)
    
    # Find initial and final states (first and last points)
    initial_energy = energies[0]
    final_energy = energies[-1]
    initial_screen = screen_numbers[0]
    final_screen = screen_numbers[-1]
    
    # Find maximum and minimum energy points
    max_idx = np.argmax(energies)
    min_idx = np.argmin(energies)
    max_energy = energies[max_idx]
    min_energy = energies[min_idx]
    max_screen = screen_numbers[max_idx]
    min_screen = screen_numbers[min_idx]
    
    # Calculate energy barrier as difference between max and min
    energy_barrier = max_energy - min_energy
    
    # Calculate additional metrics
    forward_barrier = max_energy - initial_energy
    backward_barrier = max_energy - final_energy
    total_energy_change = abs(final_energy - initial_energy)
    
    return {
        'initial_energy': initial_energy,
        'final_energy': final_energy,
        'max_energy': max_energy,
        'min_energy': min_energy,
        'initial_screen': initial_screen,
        'final_screen': final_screen,
        'max_screen': max_screen,
        'min_screen': min_screen,
        'energy_barrier': energy_barrier,
        'forward_barrier': forward_barrier,
        'backward_barrier': backward_barrier,
        'total_energy_change': total_energy_change,
        'max_idx': max_idx,
        'min_idx': min_idx
    }

def process_folder(folder_path, max_screen=8, base_path=None, length_factor=1.0):
    """
    Process a single folder and extract energy data from screen files.
    Returns a dictionary with screen numbers and corresponding energies.
    """
    folder_name = os.path.basename(folder_path)
    
    # Create hierarchical name for subfolders (structure/pct/L_R format)
    if base_path and folder_path.startswith(base_path):
        relative_path = os.path.relpath(folder_path, base_path)
        if relative_path != folder_name:  # It's a subfolder
            # Replace path separators with underscores
            hierarchical_name = relative_path.replace(os.sep, '_')
        else:
            hierarchical_name = folder_name
    else:
        hierarchical_name = folder_name
    
    # Look for neb_1.data in the current folder to get length factor
    local_neb_data_file = os.path.join(folder_path, "neb_1.data")
    if os.path.exists(local_neb_data_file):
        local_length_factor = extract_length_from_neb_data(local_neb_data_file)
        if local_length_factor is not None:
            length_factor = local_length_factor
            print(f"Found local neb_1.data, using length factor: {length_factor:.6f}")
        else:
            print(f"Could not extract length from local neb_1.data, using factor = {length_factor:.6f}")
    else:
        print(f"No local neb_1.data found, using factor = {length_factor:.6f}")
    
    energies = []
    screen_numbers = []
    
    print(f"\nProcessing folder: {folder_name}")
    print(f"Using length factor: {length_factor:.6f}")
    print("-" * 50)
    
    # Check for screen files from 0 to max_screen
    for i in range(max_screen + 1):
        screen_file = os.path.join(folder_path, f"screen.{i}")
        if os.path.exists(screen_file):
            energy = extract_energy_final(screen_file, length_factor)
            if energy is not None:
                energies.append(energy)
                screen_numbers.append(i)
                print(f"  screen.{i}: {energy:.6f} (normalized)")
            else:
                print(f"  screen.{i}: N/A")
        else:
            warnings.warn(f"screen.{i} file not found in {folder_path}")
            print(f"  screen.{i}: File not found")
    
    # Calculate energy barrier
    barrier_info = calculate_energy_barrier(energies, screen_numbers)
    
    return {
        'folder_name': folder_name,
        'hierarchical_name': hierarchical_name,
        'screen_numbers': screen_numbers,
        'energies': energies,
        'folder_path': folder_path,
        'barrier_info': barrier_info,
        'length_factor': length_factor
    }

def create_output_folder(base_path):
    """Create a dedicated output folder for results."""
    output_folder = os.path.join(base_path, "energy_analysis_results")
    if os.path.exists(output_folder):
        # Remove existing folder and create new one
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)
    return output_folder

def plot_individual_folders(data_list, output_folder):
    """Create individual plots for each folder with energy barrier annotations."""
    print(f"\nCreating individual plots...")
    
    for data in data_list:
        if not data['energies']:
            print(f"Skipping {data['folder_name']} - no energy data found")
            continue
            
        plt.figure(figsize=(12, 8))
        
        # Plot the energy curve
        plt.plot(data['screen_numbers'], data['energies'], 'bo-', 
                linewidth=2, markersize=8, label='Energy Final')
        
        # Add barrier information if available
        if data['barrier_info']:
            barrier = data['barrier_info']
            
            # Highlight initial, final, max, and min states
            plt.scatter([barrier['initial_screen']], [barrier['initial_energy']], 
                       color='green', s=150, marker='s', label='Initial State', zorder=5)
            plt.scatter([barrier['final_screen']], [barrier['final_energy']], 
                       color='blue', s=150, marker='o', label='Final State', zorder=5)
            plt.scatter([barrier['max_screen']], [barrier['max_energy']], 
                       color='red', s=150, marker='^', label='Max Energy', zorder=5)
            plt.scatter([barrier['min_screen']], [barrier['min_energy']], 
                       color='orange', s=150, marker='v', label='Min Energy', zorder=5)
            
            # Add energy barrier annotation
            plt.annotate(f'Energy Barrier: {barrier["energy_barrier"]:.5f}', 
                        xy=(barrier['max_screen'], barrier['max_energy']),
                        xytext=(10, 20), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
                        fontsize=10, fontweight='bold')
            
            # Add additional metrics
            plt.annotate(f'Forward: {barrier["forward_barrier"]:.5f}', 
                        xy=(barrier['max_screen'], barrier['max_energy']),
                        xytext=(10, -20), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
                        fontsize=9)
        
        plt.xlabel('Screen Number', fontsize=12, fontweight='bold')
        plt.ylabel('Energy Final (Normalized)', fontsize=12, fontweight='bold')
        plt.title(f'Energy Final vs Screen Number - {data["folder_name"]} (Normalized by Length)', 
                 fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Add value labels on the points
        for x, y in zip(data['screen_numbers'], data['energies']):
            plt.annotate(f'{y:.5f}', (x, y), textcoords="offset points", 
                        xytext=(0,10), ha='center', fontsize=9)
        
        plt.tight_layout()
        
        # Save individual plot using hierarchical name
        plot_file = os.path.join(output_folder, f"{data['hierarchical_name']}.png")
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"  Saved: {plot_file}")

def plot_comparative(data_list, output_folder):
    """Create comparative plots showing all folders together."""
    # This function is now disabled - no comparative plots needed
    pass

def save_data_summary(data_list, output_folder):
    """Save all data to CSV and text files with energy barrier information."""
    print(f"\nSaving data summary...")
    
    # Create comprehensive data summary
    all_data = []
    for data in data_list:
        for screen_num, energy in zip(data['screen_numbers'], data['energies']):
            all_data.append({
                'folder_name': data['folder_name'],
                'screen_number': screen_num,
                'energy_final': energy
            })
    
    # Save to CSV
    df = pd.DataFrame(all_data)
    csv_file = os.path.join(output_folder, "energy_data_summary.csv")
    df.to_csv(csv_file, index=False)
    print(f"  Saved: {csv_file}")
    
    # Save energy barrier summary
    barrier_data = []
    for data in data_list:
        if data['barrier_info']:
            barrier = data['barrier_info']
            barrier_data.append({
                'folder_name': data['folder_name'],
                'initial_energy': barrier['initial_energy'],
                'final_energy': barrier['final_energy'],
                'max_energy': barrier['max_energy'],
                'min_energy': barrier['min_energy'],
                'initial_screen': barrier['initial_screen'],
                'final_screen': barrier['final_screen'],
                'max_screen': barrier['max_screen'],
                'min_screen': barrier['min_screen'],
                'energy_barrier': barrier['energy_barrier'],
                'forward_barrier': barrier['forward_barrier'],
                'backward_barrier': barrier['backward_barrier'],
                'total_energy_change': barrier['total_energy_change']
            })
    
    if barrier_data:
        barrier_df = pd.DataFrame(barrier_data)
        barrier_csv_file = os.path.join(output_folder, "energy_barrier_summary.csv")
        barrier_df.to_csv(barrier_csv_file, index=False)
        print(f"  Saved: {barrier_csv_file}")
    
    # Save individual folder data
    for data in data_list:
        if not data['energies']:
            continue
            
        folder_data_file = os.path.join(output_folder, f"energy_data_{data['hierarchical_name']}.txt")
        with open(folder_data_file, 'w') as f:
            f.write(f"Energy Data for {data['folder_name']}\n")
            f.write("=" * 50 + "\n")
            f.write(f"Length Factor: {data['length_factor']:.6f}\n")
            f.write(f"Energy values are normalized by length factor\n")
            f.write("Screen Number\tEnergy Final (Normalized)\n")
            f.write("-" * 40 + "\n")
            for screen_num, energy in zip(data['screen_numbers'], data['energies']):
                f.write(f"screen.{screen_num}\t{energy:.6f}\n")
            
            # Add barrier information
            if data['barrier_info']:
                barrier = data['barrier_info']
                f.write("\n" + "=" * 50 + "\n")
                f.write("ENERGY BARRIER ANALYSIS\n")
                f.write("=" * 50 + "\n")
                f.write(f"Initial State (Screen {barrier['initial_screen']}): {barrier['initial_energy']:.6f}\n")
                f.write(f"Final State (Screen {barrier['final_screen']}): {barrier['final_energy']:.6f}\n")
                f.write(f"Max Energy (Screen {barrier['max_screen']}): {barrier['max_energy']:.6f}\n")
                f.write(f"Min Energy (Screen {barrier['min_screen']}): {barrier['min_energy']:.6f}\n")
                f.write(f"Energy Barrier (Max - Min): {barrier['energy_barrier']:.6f}\n")
                f.write(f"Forward Barrier (Max - Initial): {barrier['forward_barrier']:.6f}\n")
                f.write(f"Backward Barrier (Max - Final): {barrier['backward_barrier']:.6f}\n")
                f.write(f"Total Energy Change (Final - Initial): {barrier['total_energy_change']:.6f}\n")
        
        print(f"  Saved: {folder_data_file}")

def main():
    # Use current directory as base path
    base_path = os.getcwd()
    print(f"Using current directory as base path: {base_path}")
    
    # Look for neb_1.data file to extract length factor
    length_factor = 1.0
    neb_data_file = os.path.join(base_path, "neb_1.data")
    if os.path.exists(neb_data_file):
        length_factor = extract_length_from_neb_data(neb_data_file)
        if length_factor is not None:
            print(f"Found neb_1.data, extracted length factor: {length_factor:.6f}")
        else:
            print("Could not extract length from neb_1.data, using factor = 1.0")
            length_factor = 1.0
    else:
        print("neb_1.data not found, using length factor = 1.0")
    
    # Automatically discover folders
    folder_paths = discover_folders(base_path)
    
    if not folder_paths:
        print("No valid folders found!")
        return
    
    print(f"Found {len(folder_paths)} folders to process:")
    for folder in folder_paths:
        print(f"  - {os.path.basename(folder)}")
    
    # Create output folder
    output_folder = create_output_folder(base_path)
    print(f"\nOutput folder created: {output_folder}")
    
    # Process all folders
    data_list = []
    for folder_path in folder_paths:
        data = process_folder(folder_path, max_screen=8, base_path=base_path, length_factor=length_factor)
        data_list.append(data)
    
    # Generate plots and save data
    plot_individual_folders(data_list, output_folder)
    plot_comparative(data_list, output_folder)
    save_data_summary(data_list, output_folder)
    
    # Print summary statistics
    print(f"\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    
    for data in data_list:
        if not data['energies']:
            continue
            
        energies = data['energies']
        print(f"\n{data['folder_name']}:")
        print(f"  Data points: {len(energies)}")
        print(f"  Min Energy: {min(energies):.6f}")
        print(f"  Max Energy: {max(energies):.6f}")
        print(f"  Energy Range: {max(energies) - min(energies):.6f}")
        print(f"  Average Energy: {np.mean(energies):.6f}")
        
        # Add barrier information
        if data['barrier_info']:
            barrier = data['barrier_info']
            print(f"  ENERGY BARRIER ANALYSIS:")
            print(f"    Initial State (Screen {barrier['initial_screen']}): {barrier['initial_energy']:.6f}")
            print(f"    Final State (Screen {barrier['final_screen']}): {barrier['final_energy']:.6f}")
            print(f"    Max Energy (Screen {barrier['max_screen']}): {barrier['max_energy']:.6f}")
            print(f"    Min Energy (Screen {barrier['min_screen']}): {barrier['min_energy']:.6f}")
            print(f"    Energy Barrier (Max - Min): {barrier['energy_barrier']:.6f}")
            print(f"    Forward Barrier (Max - Initial): {barrier['forward_barrier']:.6f}")
            print(f"    Backward Barrier (Max - Final): {barrier['backward_barrier']:.6f}")
            print(f"    Total Energy Change (Final - Initial): {barrier['total_energy_change']:.6f}")
    
    print(f"\nAll results saved in: {output_folder}")
    print("Files generated:")
    print("  - Individual plots: energy_vs_screen_[hierarchical_name].png")
    print("  - Data summary: energy_data_summary.csv")
    print("  - Energy barrier summary: energy_barrier_summary.csv")
    print("  - Individual data: energy_data_[hierarchical_name].txt")
    print(f"\nNote: All energy values are normalized by length factor: {length_factor:.6f}")

if __name__ == "__main__":
    main()
