#!/usr/bin/env python3
"""
Script to extract Energy final values from screen files and plot them.
X-axis: Screen number, Y-axis: Energy
"""

import os
import re
import matplotlib.pyplot as plt
import numpy as np

def extract_energy_final(screen_file):
    """
    Extract Energy final value from a screen file.
    Returns the energy value or None if not found.
    """
    try:
        with open(screen_file, 'r') as f:
            content = f.read()
        
        # Look for the pattern: Energy initial, next-to-last, final = 
        # followed by three numbers on the next line
        pattern = r'Energy initial, next-to-last, final = \s*\n\s*([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)'
        match = re.search(pattern, content)
        
        if match:
            # Return the third value (final energy)
            return float(match.group(3))
        else:
            print(f"Warning: Could not find Energy final in {screen_file}")
            return None
            
    except FileNotFoundError:
        print(f"Error: File {screen_file} not found")
        return None
    except Exception as e:
        print(f"Error reading {screen_file}: {e}")
        return None

def main():
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find all screen files (screen.0, screen.1, ..., screen.8)
    screen_files = []
    screen_numbers = []
    energies = []
    
    # Check for screen files from 0 to 8
    for i in range(9):  # 0 to 8
        screen_file = os.path.join(script_dir, f"screen.{i}")
        if os.path.exists(screen_file):
            screen_files.append(screen_file)
            screen_numbers.append(i)
            
            # Extract energy
            energy = extract_energy_final(screen_file)
            if energy is not None:
                energies.append(energy)
            else:
                energies.append(np.nan)  # Use NaN for missing values
        else:
            print(f"Warning: screen.{i} not found")
    
    # Print the results
    print("Screen Number\tEnergy Final")
    print("-" * 40)
    for i, (screen_num, energy) in enumerate(zip(screen_numbers, energies)):
        if not np.isnan(energy):
            print(f"screen.{screen_num}\t{energy:.6f}")
        else:
            print(f"screen.{screen_num}\tN/A")
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    plt.plot(screen_numbers, energies, 'bo-', linewidth=2, markersize=10, 
             markerfacecolor='lightblue', markeredgecolor='darkblue', 
             markeredgewidth=2, label='Energy Final')
    
    plt.xlabel('Screen Number', fontsize=14, fontweight='bold')
    plt.ylabel('Energy Final', fontsize=14, fontweight='bold')
    plt.title('Energy Final vs Screen Number', fontsize=16, fontweight='bold')
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.legend(fontsize=12)
    
    # Set x-axis to show integer values
    plt.xticks(screen_numbers, fontsize=12)
    plt.yticks(fontsize=12)
    
    # Add value labels on the points
    for i, (x, y) in enumerate(zip(screen_numbers, energies)):
        if not np.isnan(y):
            plt.annotate(f'{y:.2f}', (x, y), textcoords="offset points", 
                        xytext=(0,15), ha='center', fontsize=10, 
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
    
    # Format y-axis to show scientific notation if needed
    plt.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))
    
    plt.tight_layout()
    
    # Save the plot
    output_file = os.path.join(script_dir, 'energy_vs_screen.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\nPlot saved to: {output_file}")
    
    # Show the plot
    plt.show()
    
    # Also save data to a text file
    data_file = os.path.join(script_dir, 'energy_data.txt')
    with open(data_file, 'w') as f:
        f.write("Screen Number\tEnergy Final\n")
        f.write("-" * 40 + "\n")
        for screen_num, energy in zip(screen_numbers, energies):
            if not np.isnan(energy):
                f.write(f"screen.{screen_num}\t{energy:.6f}\n")
            else:
                f.write(f"screen.{screen_num}\tN/A\n")
    
    print(f"Data saved to: {data_file}")
    
    # Print summary statistics
    valid_energies = [e for e in energies if not np.isnan(e)]
    if valid_energies:
        print(f"\nSummary Statistics:")
        print(f"Number of data points: {len(valid_energies)}")
        print(f"Min Energy: {min(valid_energies):.6f}")
        print(f"Max Energy: {max(valid_energies):.6f}")
        print(f"Energy Range: {max(valid_energies) - min(valid_energies):.6f}")
        print(f"Average Energy: {np.mean(valid_energies):.6f}")

if __name__ == "__main__":
    main()

