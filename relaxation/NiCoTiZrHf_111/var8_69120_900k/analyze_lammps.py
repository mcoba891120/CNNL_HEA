import numpy as np
import csv
from ase import Atoms
from ase.io import read
from ase.neighborlist import NeighborList
from collections import defaultdict, Counter

def analyze_nearest_neighbors(filename, num_neighbors=8, output_csv="neighbor_analysis.csv"):
    # 读取 LAMMPS 数据文件
    atoms = read(filename, format='lammps-data', style='atomic')

    # 获取唯一的原子类型
    unique_types = set(atoms.get_atomic_numbers())

    # 创建原子类型到元素的映射
    type_to_element = {}
    for atomic_number in unique_types:
        element = atoms[atoms.get_atomic_numbers() == atomic_number][0].symbol
        type_to_element[atomic_number] = element
    
    print("检测到的原子类型:", type_to_element)

    # 将原子类型转换为元素符号
    chemical_symbols = [type_to_element[atom.number] for atom in atoms]
    atoms.set_chemical_symbols(chemical_symbols)

    # 创建邻居列表（使用较大的截断半径以确保至少有 8 个邻居）
    cutoff = 6.0  # 可能需要根据您的系统调整这个值
    nl = NeighborList([cutoff/2]*len(atoms), self_interaction=False, bothways=True)
    nl.update(atoms)

    # 获取所有原子类型
    atom_types = set(atoms.get_chemical_symbols())

    # 为每种原子类型初始化邻居计数
    neighbor_counts = {atom_type: defaultdict(int) for atom_type in atom_types}
    total_counts = {atom_type: 0 for atom_type in atom_types}

    # 分析每个原子的最近 8 个邻居
    for i, atom in enumerate(atoms):
        indices, offsets = nl.get_neighbors(i)
        atom_type = atom.symbol
        
        # 计算到所有邻居的距离
        neighbor_positions = atoms.positions[indices] + np.dot(offsets, atoms.get_cell())
        distances = np.linalg.norm(neighbor_positions - atoms.positions[i], axis=1)
        
        # 选择最近的 8 个邻居
        nearest_indices = indices[np.argsort(distances)[:num_neighbors]]
        nearest_types = [atoms[j].symbol for j in nearest_indices]
        
        # 统计最近邻居的类型
        type_counts = Counter(nearest_types)
        for neighbor_type, count in type_counts.items():
            neighbor_counts[atom_type][neighbor_type] += count
            total_counts[atom_type] += count

    # 写入 CSV 文件
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
analyze_nearest_neighbors("relaxation/NiCoTiZrHf_111/var8_69120_900k/after_relax.data", num_neighbors=8)
