from ase.io import read

# Load the LAMMPS data file
file_path = 'NiCoTiZrHf_69120.lmp'
atoms = read(file_path, format='lammps-data', style='atomic')

# Extract atom types and their corresponding counts in two segments
first_segment = atoms[:34560]
second_segment = atoms[34560:]

# Count atom types in both segments
first_segment_counts = {atom: first_segment.get_atomic_numbers().tolist().count(atom) for atom in set(first_segment.get_atomic_numbers())}
second_segment_counts = {atom: second_segment.get_atomic_numbers().tolist().count(atom) for atom in set(second_segment.get_atomic_numbers())}

print("First segment counts:", first_segment_counts)
print("Second segment counts:", second_segment_counts)
