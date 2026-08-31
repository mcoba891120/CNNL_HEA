import os
import numpy as np
import ase.io
from ase.io.lammpsdata import read_lammps_data
import math
from ovito.io import import_file, export_file
from ovito.modifiers import DislocationAnalysisModifier, ExpressionSelectionModifier
from ovito.data import DislocationNetwork
import WarrenCowleyParameters as wc
import pandas as pd

def get_dislocation_atoms(filename, rcut=3.1):
    """
    識別dislocation附近的原子
    """
    # 獲取dislocation line points
    pipeline = import_file(filename)
    modifier = DislocationAnalysisModifier()
    modifier.input_crystal_structure = DislocationAnalysisModifier.Lattice.BCC
    modifier.defect_mesh_smoothing_level = 10
    modifier.trial_circuit_length = 30
    modifier.circuit_stretchability = 10
    modifier.line_point_separation = 0.5
    pipeline.modifiers.append(modifier)
    data = pipeline.compute()
    
    # 提取所有dislocation line points
    linepoints = []
    for segment in data.dislocations.segments:
        for i in range(len(segment.points)):
            linepoints.append([segment.points[i][0], segment.points[i][1], segment.points[i][2]])
    
    if len(linepoints) == 0:
        print("Warning: No dislocation lines found!")
        return []
    
    linepoints = np.array(linepoints)
    
    # 讀取原子結構
    ztype = {1:28, 2:27, 3:22, 4:40, 5:72}
    atoms = read_lammps_data(filename, atom_style="atomic", Z_of_type=ztype)
    pos = atoms.get_positions()
    natoms = len(atoms)
    cell = atoms.cell.cellpar()
    
    # 找到dislocation附近的所有原子
    dislocation_atoms = []
    for i in range(natoms):
        atom_pos = pos[i]
        min_dist = float('inf')
        
        # 計算原子到所有dislocation line points的最小距離
        for line_pos in linepoints:
            dist = get_dist(atom_pos, line_pos, cell)
            if dist < min_dist:
                min_dist = dist
        
        if min_dist <= rcut:
            dislocation_atoms.append(i)
    
    return dislocation_atoms

def get_dist(atom_pos, line_pos, cell):
    """
    計算考慮週期性邊界條件的距離
    """
    lenx = cell[0]
    leny = cell[1] 
    lenz = cell[2]
    
    dispx = atom_pos[0] - line_pos[0]
    if dispx > 0.5 * lenx: dispx -= lenx
    if dispx < -0.5 * lenx: dispx += lenx
    
    dispy = atom_pos[1] - line_pos[1]
    if dispy > 0.5 * leny: dispy -= leny
    if dispy < -0.5 * leny: dispy += leny
    
    dispz = atom_pos[2] - line_pos[2]
    if dispz > 0.5 * lenz: dispz -= lenz
    if dispz < -0.5 * lenz: dispz += lenz
    
    dist = math.sqrt(dispx**2 + dispy**2 + dispz**2)
    return dist

def select_atoms_in_ovito(pipeline, atom_indices):
    """
    在OVITO pipeline中選中指定的原子
    """
    try:
        from ovito.modifiers import PythonScriptModifier
        
        def modify_selection(frame, data):
            # 初始化所有原子為未選中
            selection = np.zeros(data.particles.count, dtype=bool)
            # 選中指定的原子
            if len(atom_indices) > 0:
                selection[atom_indices] = True
            data.particles_.create_property('Selection', data=selection)
        
        pipeline.modifiers.append(PythonScriptModifier(function=modify_selection))
        return pipeline, True
        
    except ImportError:
        print("Warning: PythonScriptModifier not available. Will analyze all atoms instead.")
        return pipeline, False

# 主程式
# 使用固定的dislocation分析文件
dislocation_file = "dislocation/practice_dislocation/v3_trial3/NEB_new/screw_b111_p110_NEB/large/next3/neb_4.data"
rcut = 3.1  # dislocation附近的截止距離

print("Analyzing dislocation structure...")
try:
    dislocation_atom_ids = get_dislocation_atoms(dislocation_file, rcut)
    print(f"Found {len(dislocation_atom_ids)} atoms near dislocation lines")
    if len(dislocation_atom_ids) == 0:
        print("No dislocation atoms found! Check your dislocation analysis parameters.")
        exit()
except Exception as e:
    print(f"Error analyzing dislocation: {e}")
    exit()

# 直接對同一個data文件計算Warren-Cowley parameters
print(f"Calculating Warren-Cowley parameters for dislocation atoms in {dislocation_file}")

# 載入data文件
pipeline = import_file(dislocation_file)

# 選中dislocation附近的原子
pipeline, selection_success = select_atoms_in_ovito(pipeline, dislocation_atom_ids)

if selection_success:
    only_selected = True
    print(f"Calculating Warren-Cowley parameters for {len(dislocation_atom_ids)} selected atoms")
else:
    only_selected = False
    print("Warning: Could not select atoms, calculating for all atoms")

# 計算Warren-Cowley parameters
mod = wc.WarrenCowleyParameters(nneigh=[0, 8, 14], only_selected=only_selected)
pipeline.modifiers.append(mod)

try:
    data = pipeline.compute()
    
    # 檢查是否成功計算
    if "Warren-Cowley parameters" not in data.attributes:
        print("Error: Warren-Cowley parameters not found in computed data")
        print("Available attributes:", list(data.attributes.keys()))
        exit()
    
    wc_for_shells = data.attributes["Warren-Cowley parameters"]
    print(f"Number of shells computed: {len(wc_for_shells)}")
    
    # 處理結果 - 檢查矩陣大小
    print(f"Warren-Cowley matrix shape: {np.array(wc_for_shells[0]).shape}")
    
    # 創建正確大小的DataFrame
    wc_1nn_array = np.array(wc_for_shells[0])
    wc_2nn_array = np.array(wc_for_shells[1])
    
    # 根據實際矩陣大小設定列名和索引
    element_names = ['Ni', 'Co', 'Ti', 'Zr', 'Hf']
    n_elements = wc_1nn_array.shape[0]
    
    if n_elements == 5:
        columns = element_names
        index = element_names
    elif n_elements == 4:
        columns = element_names[:4]
        index = element_names[:4]
    else:
        columns = [f'Element_{i+1}' for i in range(n_elements)]
        index = columns
    
    wc_1nn = pd.DataFrame(wc_1nn_array, columns=columns, index=index)
    wc_2nn = pd.DataFrame(wc_2nn_array, columns=columns, index=index)
    
    print(f"1NN Warren-Cowley parameters for {'selected' if selection_success else 'all'} dislocation atoms:")
    print(wc_1nn)
    print(f"\n2NN Warren-Cowley parameters for {'selected' if selection_success else 'all'} dislocation atoms:")
    print(wc_2nn)
    
    # 保存結果
    filename_1nn = './warren_cowley_dislocation_1nn.csv'
    filename_2nn = './warren_cowley_dislocation_2nn.csv'
    
    wc_1nn.to_csv(filename_1nn)
    wc_2nn.to_csv(filename_2nn)
    
    print(f"\nResults saved to:")
    print(f"  - {filename_1nn}")
    print(f"  - {filename_2nn}")
    print(f"  - Number of atoms analyzed: {len(dislocation_atom_ids) if selection_success else 'all atoms'}")
    
    # 創建視覺化文件：將選中的原子改為Ag
    print(f"\nCreating visualization file with selected atoms marked as Ag...")
    
    # 讀取原始結構
    ztype = {1:28, 2:27, 3:22, 4:40, 5:72}  # {type: atomic_number}
    atoms = read_lammps_data(dislocation_file, atom_style="atomic", Z_of_type=ztype)
    atomic_numbers = atoms.get_atomic_numbers().copy()  # 複製一份避免修改原始數據
    
    # 將選中的原子改為Ag (原子序數47)
    for atom_id in dislocation_atom_ids:
        atomic_numbers[atom_id] = 47  # Ag的原子序數
    
    # 更新原子類型
    atoms.set_atomic_numbers(atomic_numbers)
    
    # 輸出新的data文件
    output_filename = "dislocation_selected_atoms.data"
    ase.io.write(output_filename, atoms, format="lammps-data", 
                 specorder=["Ni","Co","Ti","Zr","Hf","Ag"], masses=True)
    
    print(f"  - Visualization file saved: {output_filename}")
    print(f"    Selected dislocation atoms ({len(dislocation_atom_ids)}) are now marked as Ag")
    
    # 額外分析：顯示dislocation附近原子的元素分布
    print("\nElemental composition of dislocation atoms (original elements):")
    element_names = {28:'Ni', 27:'Co', 22:'Ti', 40:'Zr', 72:'Hf'}
    
    # 重新讀取原始文件來獲取正確的元素分布
    original_atoms = read_lammps_data(dislocation_file, atom_style="atomic", Z_of_type=ztype)
    original_atomic_numbers = original_atoms.get_atomic_numbers()
    
    element_counts = {}
    total_dislocation_atoms = len(dislocation_atom_ids)
    
    for atom_id in dislocation_atom_ids:
        element = original_atomic_numbers[atom_id]
        element_name = element_names.get(element, f'Element_{element}')
        element_counts[element_name] = element_counts.get(element_name, 0) + 1
    
    print("Element distribution in dislocation region:")
    for element, count in element_counts.items():
        ratio = count / total_dislocation_atoms
        print(f"  {element}: {count} atoms ({ratio:.3f})")
        
except Exception as e:
    print(f"Error calculating Warren-Cowley parameters: {e}")
    import traceback
    traceback.print_exc()