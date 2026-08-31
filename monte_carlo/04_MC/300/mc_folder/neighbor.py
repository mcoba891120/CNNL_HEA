from ase import Atoms
import numpy as np

def read_custom_lammps_data(filepath):
    atoms = []
    with open(filepath, 'r') as file:
        atoms_section = False
        for line in file:
            if "Atoms" in line:
                atoms_section = True
                continue
            if "Velocities" in line:  # 确保我们不读取速度数据
                break
            if atoms_section:
                if line.strip():  # 避免空行
                    parts = line.split()
                    if len(parts) < 5:  # 确保每行有足够的数据点
                        continue
                    atom_id = int(parts[0])
                    atom_type = int(parts[1])
                    x, y, z = map(float, parts[2:5])
                    atoms.append((atom_type, (x, y, z)))
    
    # 创建ASE的Atoms对象
    numbers = [atom[0] for atom in atoms]  # 直接使用原子类型作为原子序号
    positions = [atom[1] for atom in atoms]
    ase_atoms = Atoms(numbers=numbers, positions=positions)
    return ase_atoms

def find_nearest_neighbors(atoms, n_neighbors=8):
    # 初始化一个空的字典来存储邻居信息
    neighbor_types = {number: [] for number in set(atoms.get_atomic_numbers())}
    positions = atoms.get_positions()
    for i, position in enumerate(positions):
        distances = np.linalg.norm(positions - position, axis=1)
        nearest_indices = np.argsort(distances)[1:n_neighbors+1]
        types = [atoms[j].number for j in nearest_indices]
        neighbor_types[atoms[i].number].append(types)
    return neighbor_types

def main(filepath):
    ase_atoms = read_custom_lammps_data(filepath)
    neighbor_types = find_nearest_neighbors(ase_atoms)

    # 统计每种原子类型的邻近原子比例
    for atom_type in neighbor_types:
        total_neighbors = sum(len(neighbors) for neighbors in neighbor_types[atom_type])
        count = {number: 0 for number in set(ase_atoms.get_atomic_numbers())}
        for neighbors in neighbor_types[atom_type]:
            for neighbor in neighbors:
                count[neighbor] += 1
        proportions = {number: count[number] / total_neighbors for number in count}
        print(f"Atom type: {atom_type}")
        for neighbor_type, proportion in proportions.items():
            print(f"  {neighbor_type}: {proportion:.2f}")

# 使用文件路径
file_path = 'emin.data'  # 请将此路径替换为你的实际文件路径
main(file_path)
