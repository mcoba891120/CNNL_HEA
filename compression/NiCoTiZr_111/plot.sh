#!/bin/bash

# Prompt the user to enter a number
read -p "Please enter the number for the directory pattern (e.g., 12240): " input_number

# Define the output file to store the paths of .txt files
output_file="txt_file_paths.txt"

# Clear the content of the output file if it exists
> $output_file

# Loop through the directories matching the pattern
for dir in var${input_number}_*; do
  if [ -d "$dir" ]; then
    # Find .txt files in the directory and append their paths to the output file
    find "$dir" -type f -name "*.txt" >> $output_file
  fi
done

echo "Paths of .txt files have been stored in $output_file"

# Execute the Python script
python3 - <<'EOF'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import re

# Define the output file from the bash script
file_list = "txt_file_paths.txt"

# Initialize lists to store strain, stress values, slopes, and temperatures
strain_values = []
stress_values = []
slopes = []
temperatures = []
file_labels = []

# Read the file list and process each .txt file
with open(file_list, 'r') as f:
    files = f.readlines()
    for file in files:
        file = file.strip()
        with open(file, 'r') as data_file:
            strain = []
            stress = []
            # Skip the header line
            next(data_file)
            for line in data_file:
                if line.strip():  # Skip empty lines
                    data = line.split()
                    strain.append(float(data[0]))  # Assuming strain is the first column
                    stress.append(float(data[1]))  # Assuming stressX is the second column
            strain_values.append(strain)
            stress_values.append(stress)
            # Perform linear fit
            fit = np.polyfit(strain, stress, 1)
            slopes.append(fit[0])
            # Extract temperature from file path
            match = re.search(r'(\d+).txt$', file)
            if match:
                temperature = int(match.group(1))
                temperatures.append(temperature)
                file_labels.append(file)
            else:
                print(f"Could not extract temperature from file name: {file}")

# Debugging information
print(f"Temperatures: {temperatures}")
print(f"Slopes: {slopes}")

# Check if temperatures and slopes have the same length
if len(temperatures) != len(slopes):
    raise ValueError("The number of extracted temperatures and slopes do not match.")

# Sort based on temperatures
sorted_indices = np.argsort(temperatures)
sorted_temperatures = np.array(temperatures)[sorted_indices]
sorted_slopes = np.array(slopes)[sorted_indices]
sorted_strain_values = [strain_values[i] for i in sorted_indices]
sorted_stress_values = [stress_values[i] for i in sorted_indices]
sorted_file_labels = [file_labels[i] for i in sorted_indices]

# Plot Strain vs StressX with Linear Fit
plt.figure(figsize=(10, 6))

for strain, stress, temp, slope in zip(sorted_strain_values, sorted_stress_values, sorted_temperatures, sorted_slopes):
    plt.plot(strain, stress, label=f'{temp}K')  # Plot data with temperature label
    fit_fn = np.poly1d([slope, 0])  # Create linear function for plotting
    plt.plot(strain, fit_fn(strain), '--', label=f'{temp}K Fit (Slope: {slope:.2f})')

plt.xlabel('Strain')
plt.ylabel('StressX')
plt.title('Strain vs StressX with Linear Fit')
plt.legend(loc='upper left', fontsize='small')
plt.grid(True)
plt.savefig('strain_vs_stressX.png')
plt.close()

# Plot Slope vs Temperature
plt.figure(figsize=(10, 6))
plt.plot(sorted_temperatures, sorted_slopes, 'o-')
plt.xlabel('Temperature (K)')
plt.ylabel('Slope')
plt.title('Slope vs Temperature')
plt.grid(True)
plt.savefig('slope_vs_temperature.png')
plt.close()
EOF
