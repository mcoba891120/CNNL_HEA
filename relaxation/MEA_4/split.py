import numpy as np
from ase.io import read, write
from ase.io import lammpsdata

# 讀取 POSCAR 文件
file_path = 'relaxation/MEA_4/POSCAR_4'
atoms = read(file_path)

# 獲取 Ni 和 Ti 原子的索引
ni_indices = [i for i, atom in enumerate(atoms) if atom.symbol == 'Ni']
ti_indices = [i for i, atom in enumerate(atoms) if atom.symbol == 'Ti']

# 檢查 Ni 和 Ti 原子的數量
num_ni = len(ni_indices)
num_ti = len(ti_indices)

print(f"Number of Ni atoms: {num_ni}")
print(f"Number of Ti atoms: {num_ti}")

# 隨機選擇適當數量的 Ni 原子並改為 Co
if num_ni >= 3375:
    np.random.seed(42)  # 設置隨機種子以確保結果可重複
    selected_ni_indices = np.random.choice(ni_indices, 3375, replace=False)
    for i in selected_ni_indices:
        atoms[i].symbol = 'Co'
else:
    print("Ni 原子的數量不足，無法選取 3375 個原子")

# 隨機選擇適當數量的 Ti 原子並改為 Zr
if num_ti >= 3375:
    np.random.seed(42)  # 設置隨機種子以確保結果可重複
    selected_ti_indices = np.random.choice(ti_indices, 3375, replace=False)
    for i in selected_ti_indices:
        atoms[i].symbol = 'Zr'
else:
    print("Ti 原子的數量不足，無法選取 3375 個原子")

# 輸出修改後的結構到新的 POSCAR 文件
output_path = 'relaxation/MEA_4/POSCAR_final'
write(output_path, atoms)

output_path = 'relaxation/MEA_4/POSCAR_final.lmp'
write(output_path, atoms, format='lammps-data')

# 輸出 LAMMPS 數據文件
lammpsdata.write_lammps_data("relaxation/MEA_4/MEA_lmp_13500", atoms, masses=True, specorder=["Ni", "Co", "Ti", "Zr"])
