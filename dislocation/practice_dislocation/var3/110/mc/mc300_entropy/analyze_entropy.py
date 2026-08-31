from mpi4py import MPI
from lammps import PyLammps
import numpy as np
import random
import os
from ase.io import read, write
from ase.neighborlist import NeighborList

def calculate_disorder(atoms, cutoff=6.0):
    nl = NeighborList([cutoff / 2] * len(atoms), self_interaction=False, bothways=True)
    nl.update(atoms)

    atom_types = atoms.get_chemical_symbols()  # 獲取每個原子的化學符號
    disorder_ratios = []

    for i in range(len(atoms)):
        # 獲取第 i 個原子的鄰居
        indices, offsets = nl.get_neighbors(i)
        distances = atoms.get_distance(i, indices, mic=True)

        # 選擇所有的第二鄰徑內的原子
        second_neighbors = [j for j, d in zip(indices, distances) if d <= cutoff]

        # 中心原子的類型
        central_atom_type = atom_types[i]

        # 計算第二鄰徑中與中心原子相同的原子數量
        same_type_count = sum(1 for j in second_neighbors if atom_types[j] == central_atom_type)

        # 計算亂度比例，越小表示無序度越高
        disorder_ratio = 1 - (same_type_count / len(second_neighbors))  # 同種原子越少，亂度越大
        disorder_ratios.append(disorder_ratio)

    return np.mean(disorder_ratios)

def monte_carlo_simulation(num_iterations, mc_temp, lammps_data_file, gpu_id=None):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    if rank == 0:
        print(f"Starting Monte Carlo simulation with {size} processes")
        print(f"Number of iterations: {num_iterations}")
        print(f"Temperature: {mc_temp} K")

    # 初始化 LAMMPS
    if rank == 0:
        os.makedirs('mc_folder', exist_ok=True)
        os.chdir('mc_folder')
        print("Created mc_folder and changed directory")

    L = PyLammps(cmdargs=["-k", "on", "g", "1", "-sf", "kk", "-pk", "kokkos", "newton", "on", "neigh", "half"])
    L.units("metal")
    L.atom_style("atomic")
    L.read_data(lammps_data_file)
    L.pair_style("snap")
    L.pair_coeff("* * ../../../../../../potentials/HEA_var3_refit20240918.snapcoeff ../../../../../../potentials/HEA_var3_refit20240918.snapparam Ni Co Hf Ti Zr Hf")  # 五元合金
    L.neighbor("1.0 bin")
    L.neigh_modify("every 1 delay 0 check yes")
    #L.minimize("0.0 0.02 5000 10000")

    if rank == 0:
        print("Initialized LAMMPS and performed initial minimization")

    L.write_data("mc_last.data")

    # 初始狀態下計算亂度
    disorder_start = calculate_disorder(L)
    disorder_min = disorder_start
    disorder_last = disorder_start

    if rank == 0:
        print(f"Initial disorder: {disorder_start}")

    naccept = 0
    count_output = 100
    count_increment = 100

    # 定義兩個子晶格的交換類型
    swap_types_sublattice1 = [(1, 2)]  # 子晶格 1: Ni 和 Co
    swap_types_sublattice2 = [(3, 4), (3, 5), (4, 5)]  # 子晶格 2: Hf, Ti, Zr

    for iter in range(1, num_iterations + 1):
        if rank == 0 and iter % 100 == 0:
            print(f"Iteration {iter}")

        # 隨機選擇交換的原子類型，根據子晶格
        if random.random() < 0.5:
            # 子晶格 1 交換 Ni 和 Co
            type1, type2 = random.choice(swap_types_sublattice1)
        else:
            # 子晶格 2 交換 Hf, Ti, Zr
            type1, type2 = random.choice(swap_types_sublattice2)

        # 執行原子交換
        L.reset_timestep(0)
        L.fix(f"1 all atom/swap 1 1 {random.randint(10000000, 99999999)} 100000000 types {type1} {type2} ke no")
        L.run(1, "post no")
        L.unfix(1)
        #L.minimize("0.0 0.02 5000 10000")
        L.run(0)
        L.write_data("current_state.data")

        # 計算交換後的亂度
        disorder_new = calculate_disorder(L)

        accept = False
        if disorder_new >= disorder_min:
            disorder_min = disorder_new
            L.write_data("disorder_min.data")
            accept = True
            reason = "Accept1"
        elif disorder_new >= disorder_last:
            accept = True
            reason = "Accept2"
        else:
            reason = "Decline"

        if rank == 0:
            with open("MC_record.txt", "a") as f:
                f.write(f"{iter} {disorder_new} {disorder_min} {reason} type_{type1}-{type2}\n")

        if accept:
            if rank == 0:
                print("Accept")
            naccept += 1
            disorder_last = disorder_new
            L.write_data("mc_last.data")
            if iter == count_output:
                L.write_data(f"mc_loop_{iter}.data")
        else:
            if rank == 0:
                print("Decline")
            # 回退到上一次狀態
            L.delete_atoms("group all")
            L.read_data("mc_last.data", "add append")

        if iter == count_output:
            count_output += count_increment
            if rank == 0:
                print(f"Saved state at iteration {iter}")

        acceptance_rate = naccept / iter
        if rank == 0:
            print(f"Acceptance rate after iteration {iter}: {acceptance_rate}")

        comm.Barrier()

    total_naccept = comm.reduce(naccept, op=MPI.SUM, root=0)

    if rank == 0:
        print(f"MC stats:\n  starting disorder = {disorder_start}\n  minimum disorder = {disorder_min}\n  accepted MC moves = {total_naccept}")


if __name__ == "__main__":
    os.environ['OMPI_MCA_opal_cuda_support'] = 'true'
    os.environ['UCX_MEMTYPE_CACHE'] = 'n'

    gpu_id = 0
    monte_carlo_simulation(num_iterations=500000, mc_temp=300, gpu_id=gpu_id,
                           lammps_data_file="dislocation/practice_dislocation/var3/110/mc/mc300_entropy/after_relax_9000.data")

