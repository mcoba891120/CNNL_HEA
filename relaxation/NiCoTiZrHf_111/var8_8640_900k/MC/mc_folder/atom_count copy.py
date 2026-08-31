import pandas as pd

# Load the file and read its contents
file_path = 'NiCoTiZrHf_8640.lmp'

with open(file_path, 'r') as file:
    content = file.readlines()

# Locate the start of the atom data section and process it
start_line_atoms = content.index('Atoms # atomic\n') + 1

# Extract atom data lines
atom_data_lines = content[start_line_atoms:]
atom_data_lines = [line.split() for line in atom_data_lines if line.strip()]

# Filter out lines that contain non-numeric data where numeric IDs and Types are expected
atom_data_cleaned = [line for line in atom_data_lines if line[0].isdigit() and line[1].isdigit()]

# Convert the cleaned atom data to a DataFrame
df_cleaned_atoms = pd.DataFrame(atom_data_cleaned, columns=['ID', 'Type', 'x', 'y', 'z'])
df_cleaned_atoms[['ID', 'Type']] = df_cleaned_atoms[['ID', 'Type']].astype(int)

# Define the ranges for the analysis
first_range_cleaned = df_cleaned_atoms[(df_cleaned_atoms['ID'] >= 1) & (df_cleaned_atoms['ID'] <= 4320)]
second_range_cleaned = df_cleaned_atoms[(df_cleaned_atoms['ID'] >= 4321) & (df_cleaned_atoms['ID'] <= 8640)]

# Count the occurrences of each atom type in the given ranges
first_range_count_cleaned = first_range_cleaned['Type'].value_counts().sort_index()
second_range_count_cleaned = second_range_cleaned['Type'].value_counts().sort_index()

# Map the type numbers to element names
element_map_cleaned = {1: 'Co', 2: 'Ni', 3: 'Ti', 4: 'Zr'}

# Convert the counts to element names
first_range_count_cleaned.index = first_range_count_cleaned.index.map(element_map_cleaned)
second_range_count_cleaned.index = second_range_count_cleaned.index.map(element_map_cleaned)

# Combine the counts into a single DataFrame for better comparison
result_df_cleaned_atoms = pd.DataFrame({'1-4320 Count': first_range_count_cleaned, '4321-8640 Count': second_range_count_cleaned})

# Print the results
print(result_df_cleaned_atoms)
