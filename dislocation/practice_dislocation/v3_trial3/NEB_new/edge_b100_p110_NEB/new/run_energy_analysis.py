#!/usr/bin/env python3
"""
Simplified script to run energy analysis on multiple folders.
Uses the configuration file to define which folders to process.
"""

import os
import sys
from folder_list_config import FOLDER_PATHS, MAX_SCREEN, OUTPUT_FOLDER_NAME, PLOT_SETTINGS, PLOT_COLORS

# Import the main analysis functions
from multi_folder_energy_analysis import (
    process_folder, 
    create_output_folder, 
    plot_individual_folders, 
    plot_comparative, 
    save_data_summary
)

def main():
    """Main function to run the energy analysis."""
    
    # Get the base path from the first folder
    base_path = os.path.dirname(FOLDER_PATHS[0]) if FOLDER_PATHS else os.getcwd()
    
    # Filter to only include existing folders
    existing_folders = [path for path in FOLDER_PATHS if os.path.exists(path)]
    
    if not existing_folders:
        print("No valid folders found!")
        print("Please check the FOLDER_PATHS in folder_list_config.py")
        return
    
    print(f"Found {len(existing_folders)} folders to process:")
    for folder in existing_folders:
        print(f"  - {os.path.basename(folder)}")
    
    # Create output folder
    output_folder = create_output_folder(base_path)
    print(f"\nOutput folder created: {output_folder}")
    
    # Process all folders
    data_list = []
    for folder_path in existing_folders:
        data = process_folder(folder_path, MAX_SCREEN, base_path)
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
        print(f"  Average Energy: {sum(energies)/len(energies):.6f}")
    
    print(f"\nAll results saved in: {output_folder}")
    print("Files generated:")
    print("  - Individual plots: energy_vs_screen_[hierarchical_name].png")
    print("  - Data summary: energy_data_summary.csv")
    print("  - Individual data: energy_data_[hierarchical_name].txt")

if __name__ == "__main__":
    main()
