import numpy as np
import csv
from ase.io import read
from ase.neighborlist import NeighborList
from collections import defaultdict, Counter

def analyze_nearest_neighbors(filename, num_neighbors=8, output_csv="neighbor_analysis.csv"):
    # 使用 ASE 讀取 LAMMPS 資料文件，指定 'lammps-data' 格式和 'atomic' 的 atom_style
    atoms = read(filename, format='lammps-data', atom_style='atomic')

    # 原子符號映射，對應資料檔案中的原子序數到化學符號
    # 更新的原子符號映射，使用正確的原子序
    symbol_map = {28: 'Ni', 27: 'Co', 72: 'Hf', 22: 'Ti', 40: 'Zr'}
    atomic_numbers = atoms.get_atomic_numbers()

    # 檢查是否所有原子序數都有對應的化學符號，避免出現 KeyError
    atom_symbols = []
    for i in atomic_numbers:
        if i in symbol_map:
            atom_symbols.append(symbol_map[i])
        else:
            raise KeyError(f"Unknown atomic number {i} found in the dataset.")

    # 設定原子的化學符號
    atoms.set_chemical_symbols(atom_symbols)

    # 設定 NeighborList，用於計算鄰近原子，cutoff 半徑為 6.0
    cutoff = 6.0
    nl = NeighborList([cutoff/2]*len(atoms), self_interaction=False, bothways=True)
    nl.update(atoms)

    atom_types = set(atoms.get_chemical_symbols())

    # 構建鄰近原子的計數和總計數字典
    neighbor_counts = {atom_type: defaultdict(int) for atom_type in atom_types}
    total_counts = {atom_type: 0 for atom_type in atom_types}

    # 遍歷所有原子，計算每個原子的鄰近原子類型及數量
    for i, atom in enumerate(atoms):
        indices, offsets = nl.get_neighbors(i)  # 找到鄰近的原子
        atom_type = atom.symbol  # 當前原子的符號
        
        neighbor_positions = atoms.positions[indices] + np.dot(offsets, atoms.get_cell())  # 鄰近原子的實際位置
        distances = np.linalg.norm(neighbor_positions - atoms.positions[i], axis=1)  # 計算距離
        
        nearest_indices = indices[np.argsort(distances)[:num_neighbors]]  # 選擇最近的 num_neighbors 個原子
        nearest_types = [atoms[j].symbol for j in nearest_indices]  # 鄰近原子的化學符號
        
        type_counts = Counter(nearest_types)
        for neighbor_type, count in type_counts.items():
            neighbor_counts[atom_type][neighbor_type] += count
            total_counts[atom_type] += count

    # 將結果寫入 CSV 檔案
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
analyze_nearest_neighbors("dislocation/practice_dislocation/perfect_HEA/b111_p110/after_relax.data", num_neighbors=8)




