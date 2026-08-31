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

def monte_carlo_swap(atoms, steps, cutoff=6.0, print_interval=100, initial_acceptance_rate=0.5, final_acceptance_rate=0.05):
    current_disorder_ratios = calculate_disorder(atoms, cutoff=cutoff)
    current_average_disorder = np.mean(current_disorder_ratios)

    all_disorder_values = [current_average_disorder]
    accepted_swaps = 0
    total_swaps = 0

    with open('final_disorder.txt', 'w') as final_file:
        final_file.write("Step\tAverage_Disorder_Ratio\n")
        final_file.flush()
        os.fsync(final_file.fileno())
        
        for step in range(steps):
            i, j = random.sample(range(len(atoms)), 2)
            atom_i_type = atoms[i].symbol
            atom_j_type = atoms[j].symbol
            total_swaps += 1

            # 動態調整接受率：從 50% 漸變到 5%
            dynamic_acceptance_rate = initial_acceptance_rate - (initial_acceptance_rate - final_acceptance_rate) * (step / steps)
            threshold_z = -np.log(dynamic_acceptance_rate)  # 轉換為對應的 z 值閾值

            # 使用五個 if-else 判斷交換條件
            if (atom_i_type == 'Ni' and atom_j_type == 'Co') or (atom_i_type == 'Co' and atom_j_type == 'Ni'):
                atoms[i].symbol, atoms[j].symbol = atoms[j].symbol, atoms[i].symbol
                swap_status = "Accepted"
            elif (atom_i_type == 'Ti' and atom_j_type == 'Zr') or (atom_i_type == 'Zr' and atom_j_type == 'Ti'):
                atoms[i].symbol, atoms[j].symbol = atoms[j].symbol, atoms[i].symbol
                swap_status = "Accepted"
            elif (atom_i_type == 'Ti' and atom_j_type == 'Hf') or (atom_i_type == 'Hf' and atom_j_type == 'Ti'):
                atoms[i].symbol, atoms[j].symbol = atoms[j].symbol, atoms[i].symbol
                swap_status = "Accepted"
            elif (atom_i_type == 'Zr' and atom_j_type == 'Hf') or (atom_i_type == 'Hf' and atom_j_type == 'Zr'):
                atoms[i].symbol, atoms[j].symbol = atoms[j].symbol, atoms[i].symbol
                swap_status = "Accepted"
            else:
                swap_status = "Rejected"

            if swap_status == "Accepted":
                new_disorder_ratios = calculate_disorder(atoms, cutoff=cutoff)
                new_average_disorder = np.mean(new_disorder_ratios)
                delta_disorder = new_average_disorder - current_average_disorder

                # 計算 Z 值
                if len(all_disorder_values) >= 10:
                    recent_values = all_disorder_values[-10:]
                    mean_val = np.mean(recent_values)
                    std_val = np.std(recent_values)
                    z = (new_average_disorder - mean_val) / std_val if std_val > 0 else -np.inf
                else:
                    z = -np.inf

                # 判斷是否接受新的交換結果
                if delta_disorder > 0 or z >= threshold_z:
                    current_disorder_ratios = new_disorder_ratios
                    current_average_disorder = new_average_disorder
                    all_disorder_values.append(new_average_disorder)
                    accepted_swaps += 1
                else:
                    # 還原交換
                    atoms[i].symbol, atoms[j].symbol = atoms[j].symbol, atoms[i].symbol

            # 在每一步寫入總的 disorder
            final_file.write(f"{step}\t{current_average_disorder:.6f}\n")
            final_file.flush()
            os.fsync(final_file.fileno())

            if step % print_interval == 0:
                write_disorder_to_file(atoms, current_disorder_ratios, f'disorder_step_{step}.txt')

    # 計算並打印接受率
    acceptance_rate = accepted_swaps / total_swaps if total_swaps > 0 else 0
    # 將總交換次數、被接受的交換次數和接受率寫入新的檔案
    with open('acceptance_rate.txt', 'w') as rate_file:
        rate_file.write(f"Total Swaps: {total_swaps}\n")
        rate_file.write(f"Accepted Swaps: {accepted_swaps}\n")
        rate_file.write(f"Acceptance Rate: {acceptance_rate:.4f}\n")

    return atoms


# 讀取初始系統
atoms = read('after_relax_9000.data', format='lammps-data', atom_style='atomic')
# 執行蒙地卡羅交換
atoms = monte_carlo_swap(atoms, steps=500000, cutoff=6.0, print_interval=100)
# 輸出最終結果
write('final_mc_high_entropy.data', atoms, format='lammps-data')



