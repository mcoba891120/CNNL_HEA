import numpy as np
import csv
from ase import Atoms
from ase.io import read
from ase.neighborlist import NeighborList
from collections import defaultdict, Counter

def analyze_nearest_neighbors(filename, num_neighbors=8, output_csv="neighbor_analysis.csv"):
    atoms = read(filename, format='lammps-data', style='atomic')

    # 原子符號映射
    # symbol_map = {1: 'Ni', 2: 'Co', 3: 'Ti', 4: 'Zr'}
    symbol_map = {28: 'Ni', 27: 'Co', 22: 'Ti', 40: 'Zr'}

    atoms.set_chemical_symbols([symbol_map[i] for i in atoms.get_atomic_numbers()])

    cutoff = 6.0
    nl = NeighborList([cutoff/2]*len(atoms), self_interaction=False, bothways=True)
    nl.update(atoms)

    atom_types = set(atoms.get_chemical_symbols())

    neighbor_counts = {atom_type: defaultdict(int) for atom_type in atom_types}
    total_counts = {atom_type: 0 for atom_type in atom_types}

    for i, atom in enumerate(atoms):
        indices, offsets = nl.get_neighbors(i)
        atom_type = atom.symbol
        
        neighbor_positions = atoms.positions[indices] + np.dot(offsets, atoms.get_cell())
        distances = np.linalg.norm(neighbor_positions - atoms.positions[i], axis=1)
        
        nearest_indices = indices[np.argsort(distances)[:num_neighbors]]
        nearest_types = [atoms[j].symbol for j in nearest_indices]
        
        type_counts = Counter(nearest_types)
        for neighbor_type, count in type_counts.items():
            neighbor_counts[atom_type][neighbor_type] += count
            total_counts[atom_type] += count

    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        header = ['Atom Type'] + [f'Neighbor {t}' for t in sorted(atom_types)]
        writer.writerow(header)

        for atom_type in sorted(atom_types):
            row = [atom_type]
            total = total_counts[atom_type]
            for neighbor_type in sorted(atom_types):
                count = neighbor_counts[atom_type][neighbor_type]
                percentage = (count / total) * 100 if total > 0 else 0
                row.append(f"{percentage:.2f}%")
            writer.writerow(row)

    print(f"分析结果已保存到 {output_csv}")

# 使用示例
analyze_nearest_neighbors("monte_carlo/var5_4000_900k/mc_folder/emin.data", num_neighbors=8)
