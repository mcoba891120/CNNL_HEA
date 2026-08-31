#!/bin/bash

# Prompt the user to enter the base directory pattern
echo "Please select the base directory pattern:"
echo "1. NiCoTiZr"
echo "2. NiCoTiZrHf"
read -p "Enter your choice (1 or 2): " base_choice

# Set the base directory pattern based on user input
if [ "$base_choice" -eq 1 ]; then
  base_pattern="NiCoTiZr"
elif [ "$base_choice" -eq 2 ]; then
  base_pattern="NiCoTiZrHf"
else
  echo "Invalid choice. Defaulting to NiCoTiZr."
  base_pattern="NiCoTiZr"
fi

# Prompt the user to enter a number
read -p "Please enter the var number (e.g. 13): " input_number

# Define the base directories
base_dirs=("compress" "relax")
# Define the output directory
output_dir="plot/var${input_number}_${base_pattern}"

# Create the output directory if it does not exist
mkdir -p "$output_dir"

# Clear the content of any previous output files
rm -f txt_file_paths_*.txt

# Function to store file paths in a temporary file
function store_file_paths {
  local ni_dir="$1"
  local ni_dir_name="$2"
  local var_dir_pattern="$3"

  echo "Searching in directory: $ni_dir"
  find "$ni_dir" -type d -name "$var_dir_pattern" | while read var_dir; do
    if [ -d "$var_dir" ]; then
      echo "Found directory: $var_dir"
      # Find .txt files in the varX_* directory and append their paths to the output file
      find "$var_dir" -type f -name "*.txt" >> "txt_file_paths_${ni_dir_name}.txt"
    else
      echo "Directory not found: $var_dir"
    fi
  done
}

# Search in compress and relax directories
for dir in "${base_dirs[@]}"; do
  find "$dir" -type d -name "${base_pattern}_*" | while read ni_dir; do
    ni_dir_name=$(basename "$ni_dir")
    var_dir_pattern="var${input_number}_*"
    store_file_paths "$ni_dir" "$ni_dir_name" "$var_dir_pattern"
  done
done

# Execute the Python script
python3 - <<EOF
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import re
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

# Define the output directory from the bash script
output_dir = "${output_dir}"
print(f"Output directory: {output_dir}")

# PDF setup
pdf_filename = os.path.join(output_dir, f"var${input_number}_${base_pattern}.pdf")

# Function to process each NiCoTiZr_* directory
def process_directory(file_list, dir_name):
    # Initialize lists to store strain, stress values, slopes, intercepts, and temperatures
    strain_values = []
    stress_values = []
    slopes = []
    intercepts = []
    temperatures = []
    file_labels = []
    combined_density_data = {}

    # Read the file list and process each .txt file
    with open(file_list, 'r') as f:
        files = f.readlines()
        for file in files:
            file = file.strip()
            print(f"Processing file: {file}")  # Debugging information
            if "SS_curve" in file:
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
                    if strain and stress:
                        strain_values.append(strain)
                        stress_values.append(stress)
                        # Perform linear fit
                        fit = np.polyfit(strain, stress, 1)
                        slopes.append(fit[0])
                        intercepts.append(fit[1])
                        # Extract temperature from file path
                        match = re.search(r'(\d+)[kK]?.txt$', file)
                        if match:
                            temperature = int(match.group(1))
                            temperatures.append(temperature)
                            file_labels.append(file)
                        else:
                            print(f"Could not extract temperature from file name: {file}")
                    else:
                        print(f"No data found in file: {file}")
            elif "Record_npt" in file:
                var_dir = os.path.dirname(file)
                var_label = var_dir.split('_')[-1]  # Extract temperature label from directory name
                if var_label not in combined_density_data:
                    combined_density_data[var_label] = {'steps': [], 'densities': []}
                with open(file, 'r') as data_file:
                    # Skip the header line
                    next(data_file)
                    for line in data_file:
                        if line.strip():  # Skip empty lines
                            data = line.split()
                            combined_density_data[var_label]['steps'].append(float(data[0]))  # Assuming step is the first column
                            combined_density_data[var_label]['densities'].append(float(data[4]))  # Assuming density is the fifth column

    # Plotting combined step vs density data
    if combined_density_data:
        plt.figure(figsize=(10, 6))
        sorted_density_data = sorted(combined_density_data.items(), key=lambda x: int(re.search(r'\d+', x[0]).group()))
        for label, data in sorted_density_data:
            steps = data['steps']
            densities = data['densities']
            avg_density = np.mean(densities)
            plt.plot(steps, densities, label=f'{label}K (Avg Density: {avg_density:.2f})')
        plt.xlabel('Step')
        plt.ylabel('Density')
        plt.title(f'Step vs Density for {dir_name}')
        plt.legend(loc='upper left', fontsize='small')
        plt.grid(True)
        combined_save_path = os.path.join(output_dir, f'step_vs_density_{dir_name}.png')
        print(f"Saving combined step vs density plot to {combined_save_path}")
        plt.savefig(combined_save_path, dpi=300)
        plt.close()

    if strain_values and stress_values:
        # Debugging information
        print(f"Temperatures: {temperatures}")
        print(f"Slopes: {slopes}")
        print(f"Intercepts: {intercepts}")

        # Check if temperatures, slopes, and intercepts have the same length
        if len(temperatures) != len(slopes) or len(temperatures) != len(intercepts):
            raise ValueError("The number of extracted temperatures, slopes, and intercepts do not match.")

        # Sort based on temperatures
        sorted_indices = np.argsort(temperatures)
        sorted_temperatures = np.array(temperatures)[sorted_indices]
        sorted_slopes = np.array(slopes)[sorted_indices]
        sorted_intercepts = np.array(intercepts)[sorted_indices]
        sorted_strain_values = [strain_values[i] for i in sorted_indices]
        sorted_stress_values = [stress_values[i] for i in sorted_indices]
        sorted_file_labels = [file_labels[i] for i in sorted_indices]

        # Plot Strain vs StressX with Linear Fit
        plt.figure(figsize=(10, 6))

        for strain, stress, temp, slope, intercept in zip(sorted_strain_values, sorted_stress_values, sorted_temperatures, sorted_slopes, sorted_intercepts):
            plt.plot(strain, stress, label=f'{temp}K')  # Plot data with temperature label
            fit_fn = np.poly1d([slope, intercept])  # Create linear function for plotting
            plt.plot(strain, fit_fn(strain), '--', label=f'{temp}K Fit (Slope: {slope:.2f})')  # Remove intercept from legend

        plt.xlabel('Strain')
        plt.ylabel('StressX')
        plt.title(f'Strain vs StressX with Linear Fit for {dir_name}')
        plt.legend(loc='upper left', fontsize='small')
        plt.grid(True)
        save_path = os.path.join(output_dir, f'strain_vs_stressX_{dir_name}.png')
        print(f"Saving strain vs stressX plot to {save_path}")
        plt.savefig(save_path, dpi=300)
        plt.close()

        # Plot Slope vs Temperature
        plt.figure(figsize=(10, 6))
        plt.plot(sorted_temperatures, sorted_slopes, 'o-')
        plt.xlabel('Temperature (K)')
        plt.ylabel('Slope')
        plt.title(f'Slope vs Temperature for {dir_name}')
        plt.grid(True)
        save_path = os.path.join(output_dir, f'slope_vs_temperature_{dir_name}.png')
        print(f"Saving slope vs temperature plot to {save_path}")
        plt.savefig(save_path, dpi=300)
        plt.close()

        return combined_save_path, [save_path, os.path.join(output_dir, f'strain_vs_stressX_{dir_name}.png')]
    else:
        return None, []

# Process each txt_file_paths_*.txt file
combined_density_plot = {}
other_plots_all = []

for file_list in os.listdir('.'):
    if file_list.startswith('txt_file_paths_') and file_list.endswith('.txt'):
        dir_name = file_list[len('txt_file_paths_'):-len('.txt')]
        density_plot, other_plots = process_directory(file_list, dir_name)
        if density_plot:
            combined_density_plot[density_plot] = density_plot
        other_plots_all.extend(other_plots)

# Create the PDF and add plots
if combined_density_plot or other_plots_all:
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    width, height = letter

    # Add density plots first
    for plot in combined_density_plot:
        c.drawImage(ImageReader(combined_density_plot[plot]), 0, 0, width, height, preserveAspectRatio=True)
        c.showPage()

    # Add other plots
    for plot in other_plots_all:
        c.drawImage(ImageReader(plot), 0, 0, width, height, preserveAspectRatio=True)
        c.showPage()

    c.save()
    print(f"PDF file saved to {pdf_filename}")

# Remove intermediate files
for file_list in os.listdir('.'):
    if file_list.startswith('txt_file_paths_') and file_list.endswith('.txt'):
        os.remove(file_list)

print(f"Done. Plots are saved in ${output_dir} and combined into a PDF file.")
EOF

echo "Script execution completed."
