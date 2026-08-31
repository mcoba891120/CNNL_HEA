import matplotlib.pyplot as plt

# Define the output file from the bash script
file_list = "txt_file_paths.txt"

# Initialize lists to store strain and stress values
strain_values = []
stress_values = []

# Read the file list and process each .txt file
with open(file_list, 'r') as f:
    files = f.readlines()
    for file in files:
        file = file.strip()
        with open(file, 'r') as data_file:
            strain = []
            stress = []
            for line in data_file:
                if line.strip():  # Skip empty lines
                    data = line.split()
                    strain.append(float(data[0]))  # Assuming strain is the first column
                    stress.append(float(data[1]))  # Assuming stressX is the second column
            strain_values.append(strain)
            stress_values.append(stress)

# Plotting
plt.figure(figsize=(10, 6))

for strain, stress in zip(strain_values, stress_values):
    plt.plot(strain, stress, label=file)

plt.xlabel('Strain')
plt.ylabel('StressX')
plt.title('Strain vs StressX')
plt.legend()
plt.grid(True)
plt.show()
