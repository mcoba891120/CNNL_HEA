import numpy as np
from ase.io import read, write
from ase.neighborlist import NeighborList
import random
import os

def calculate_disorder(atoms, cutoff=6.0):
    nl = NeighborList([cutoff / 2] * len(atoms), self_interaction=False, bothways=True)
    nl.update(atoms)
    
    atom_types = atoms.get_chemical_symbols()
    disorder_ratios = []

    for i in range(len(atoms)):
        indices, offsets = nl.get_neighbors(i)
        if len(indices) == 0:
            print(f"Warning: Atom {i} has no neighbors.")
            continue

        neighbor_positions = atoms.positions[indices] + np.dot(offsets, atoms.get_cell())
        distances = np.linalg.norm(neighbor_positions - atoms.positions[i], axis=1)

        second_neighbors = [j for j, d in zip(indices, distances) if d <= cutoff]
        central_atom_type = atom_types[i]
        different_type_count = sum(1 for j in second_neighbors if atom_types[j] != central_atom_type)
        disorder_ratio = different_type_count / len(second_neighbors) if len(second_neighbors) > 0 else 0
        disorder_ratios.append(disorder_ratio)
    
    return disorder_ratios

def write_disorder_to_file(atoms, disorder_ratios, filename):
    atom_types = atoms.get_chemical_symbols()
    with open(filename, 'w') as f:
        for i, (ratio, atom_type) in enumerate(zip(disorder_ratios, atom_types)):
            f.write(f"Atom {i+1} ({atom_type}): Disorder Ratio = {ratio:.6f}\n")

def monte_carlo_swap(atoms, steps, cutoff=6.0, print_interval=100, threshold_z=0.8):
    current_disorder_ratios = calculate_disorder(atoms, cutoff=cutoff)
    current_average_disorder = np.mean(current_disorder_ratios)

    all_disorder_values = [current_average_disorder]
    with open('final_disorder.txt', 'w') as final_file:
        final_file.write("Step\tAverage_Disorder_Ratio\n")
        final_file.flush()
        os.fsync(final_file.fileno())
        
        for step in range(steps):
            i, j = random.sample(range(len(atoms)), 2)
            atom_i_type = atoms[i].symbol
            atom_j_type = atoms[j].symbol

            # 使用五個 if-else 判斷交換條件
            if (atom_i_type == 'Ni' and atom_j_type == 'Co') or (atom_i_type == 'Co' and atom_j_type == 'Ni'):
                # 交換 Ni 和 Co
                atoms[i].symbol, atoms[j].symbol = atoms[j].symbol, atoms[i].symbol
                swap_status = "Accepted"
            elif (atom_i_type == 'Ti' and atom_j_type == 'Zr') or (atom_i_type == 'Zr' and atom_j_type == 'Ti'):
                # 交換 Ti 和 Zr
                atoms[i].symbol, atoms[j].symbol = atoms[j].symbol, atoms[i].symbol
                swap_status = "Accepted"
            elif (atom_i_type == 'Ti' and atom_j_type == 'Hf') or (atom_i_type == 'Hf' and atom_j_type == 'Ti'):
                # 交換 Ti 和 Hf
                atoms[i].symbol, atoms[j].symbol = atoms[j].symbol, atoms[i].symbol
                swap_status = "Accepted"
            elif (atom_i_type == 'Zr' and atom_j_type == 'Hf') or (atom_i_type == 'Hf' and atom_j_type == 'Zr'):
                # 交換 Zr 和 Hf
                atoms[i].symbol, atoms[j].symbol = atoms[j].symbol, atoms[i].symbol
                swap_status = "Accepted"
            else:
                swap_status = "Rejected"  # 其他情況不進行交換
            # 計算新的無序度和變化量
            if swap_status == "Accepted":
                new_disorder_ratios = calculate_disorder(atoms, cutoff=cutoff)
                new_average_disorder = np.mean(new_disorder_ratios)
                delta_disorder = new_average_disorder - current_average_disorder

                # 計算 Z 值
                if len(all_disorder_values) >= 10:
                    recent_values = all_disorder_values[-10:]
                    mean_val = np.mean(recent_values)
                    std_val = np.std(recent_values)
                    if std_val > 0:
                        z = (new_average_disorder - mean_val) / std_val
                    else:
                        z = -np.inf  # 若標準差為零，設定 Z 值為負無限
                else:
                    z = -np.inf

                # 判斷是否接受新的交換結果
                if delta_disorder > 0 or z >= threshold_z:
                    current_disorder_ratios = new_disorder_ratios
                    current_average_disorder = new_average_disorder
                    all_disorder_values.append(new_average_disorder)
                else:
                    # 若不接受變動，則還原交換
                    atoms[i].symbol, atoms[j].symbol = atoms[j].symbol, atoms[i].symbol

            # 每一步寫入總的 disorder
            final_file.write(f"{step}\t{current_average_disorder:.6f}\n")
            final_file.flush()
            os.fsync(final_file.fileno())

            # 每 10 步記錄一次均值與標準差
            if step % 10 == 0:
                if len(all_disorder_values) > 10:
                    all_disorder_values.pop(0)
                recent_values = all_disorder_values[-10:]
                mean_val = np.mean(recent_values)
                std_val = np.std(recent_values)
                with open('disorder_distribution.txt', 'a') as dist_file:
                    dist_file.write(f"Step {step}: Mean = {mean_val:.6f}, Std = {std_val:.6f}\n")
                
            if step % print_interval == 0:
                write_disorder_to_file(atoms, current_disorder_ratios, f'disorder_step_{step}.txt')

    return atoms

# 讀取初始系統
atoms = read('after_relax_9000.data', format='lammps-data', atom_style='atomic')
# 執行蒙地卡羅交換
atoms = monte_carlo_swap(atoms, steps=500000, cutoff=6.0, print_interval=100)
# 輸出最終結果
write('final_mc_high_entropy.data', atoms, format='lammps-data')



