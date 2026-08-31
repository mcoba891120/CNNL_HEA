import os
import sys
import numpy as np
import csv
from ase.io.lammpsdata import read_lammps_data
from ovito.io import import_file, export_file
from ovito.modifiers import AtomicStrainModifier
from ovito.pipeline import FileSource

def get_top_strain_points(input_file, ref_file, top_n=200, boundary_thickness=5.0):
    pipeline = import_file(input_file)
    mod = AtomicStrainModifier()
    mod.cutoff = 3.5
    mod.minimum_image_convention = True
    mod.select_invalid_particles = True
    mod.reference = FileSource(); mod.reference.load(ref_file)
    pipeline.modifiers.append(mod)

    data = pipeline.compute()
    positions = data.particles['Position'][...]
    strains = data.particles['Shear Strain'][...]

    z_vals = positions[:,2]
    zmin, zmax = z_vals.min(), z_vals.max()
    central = (z_vals > zmin + boundary_thickness) & (z_vals < zmax - boundary_thickness)

    valid_idx = np.where(~np.isnan(strains) & ~np.isinf(strains) & central)[0]
    if len(valid_idx) < top_n:
        raise RuntimeError(f"有效原子 {len(valid_idx)} 少於 top_n={top_n}")

    sorted_idx = valid_idx[np.argsort(strains[valid_idx])[::-1]]
    top_idx = sorted_idx[:top_n]
    return positions[top_idx]


def get_atoms_near_points(points, positions, cell, rcut):
    pts = np.array(points)
    pos = positions
    L = np.array(cell)
    ids = set()
    for p in pts:
        disp = pos - p
        disp = disp - np.round(disp / L) * L
        dists = np.linalg.norm(disp, axis=1)
        close = np.where(dists <= rcut)[0]
        ids.update(close.tolist())
    return list(ids)


def calculate_element_ratios(atom_ids, atomic_numbers):
    elems = {28:0,27:0,22:0,40:0,72:0}
    n = len(atom_ids)
    if n == 0:
        return {k:0.0 for k in elems}
    for i in atom_ids:
        z = atomic_numbers[i]
        if z in elems:
            elems[z] += 1
    return {k:v/n for k,v in elems.items()}


def rcut_parameter_scan(filename, ref_file, top_n=200, rcut=3.0):
    points = get_top_strain_points(filename, ref_file, top_n=top_n)

    ztype = {1:28,2:27,3:22,4:40,5:72}
    atoms = read_lammps_data(filename, atom_style='atomic', Z_of_type=ztype)
    positions = atoms.get_positions()
    numbers = atoms.get_atomic_numbers()
    cell = np.array(atoms.cell.cellpar()[:3])

    results = []
    # 使用傳入的rcut參數
    atom_ids = get_atoms_near_points(points, positions, cell, rcut)
    ratios = calculate_element_ratios(atom_ids, numbers)
    results.append({
        'rcut': rcut,
        'count': len(atom_ids),
        'top_n': top_n,
        **{f"ratio_{z}": ratios[z] for z in sorted(ratios)}
    })
    return results


def plot_atom_count(results, output_plot, title):
    import matplotlib.pyplot as plt
    rcuts = [r['rcut'] for r in results]
    counts = [r['count'] for r in results]
    plt.figure()
    plt.plot(rcuts, counts)
    plt.xlabel('rcut (Å)')
    plt.ylabel('Atom Count')
    plt.title(title)
    plt.grid(True)
    plt.savefig(output_plot, dpi=300, bbox_inches='tight')
    plt.close()


def plot_composition(results, output_plot, title):
    import matplotlib.pyplot as plt
    rcuts = [r['rcut'] for r in results]
    ratios = {z: [r[f"ratio_{z}"] for r in results] for z in [28,27,22,40,72]}
    labels = {28:'Ni',27:'Co',22:'Ti',40:'Zr',72:'Hf'}

    plt.figure(figsize=(8, 6))
    plt.suptitle(title)

    # Ni & Co
    ax1 = plt.subplot(2,1,1)
    ax1.plot(rcuts, ratios[28], label=labels[28])
    ax1.plot(rcuts, ratios[27], label=labels[27])
    ax1.axhline(0.25, linestyle='--', label='y=0.25')
    ax1.set_ylabel('Element Ratio')
    ax1.set_title('Ni & Co Ratio vs rcut')
    ax1.legend()
    ax1.legend(loc='upper right')
    ax1.grid(True)

    # Ti, Zr & Hf
    ax2 = plt.subplot(2,1,2)
    ax2.plot(rcuts, ratios[22], label=labels[22])
    ax2.plot(rcuts, ratios[40], label=labels[40])
    ax2.plot(rcuts, ratios[72], label=labels[72])
    ax2.axhline(0.5/3.0, linestyle='--', label='y=0.5/3')
    ax2.set_xlabel('rcut (Å)')
    ax2.set_ylabel('Element Ratio')
    ax2.set_title('Ti, Zr & Hf Ratio vs rcut')
    ax2.legend(loc='upper right')
    ax2.grid(True)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])  # reserve space for suptitle
    plt.savefig(output_plot, dpi=300, bbox_inches='tight')
    plt.close()


def plot_topn_analysis(results, output_plot, title):
    """繪製top_n vs 元素比例的圖表"""
    import matplotlib.pyplot as plt
    
    # 按top_n排序
    results_sorted = sorted(results, key=lambda x: x['top_n'])
    top_ns = [r['top_n'] for r in results_sorted]
    ratios = {z: [r[f"ratio_{z}"] for r in results_sorted] for z in [28,27,22,40,72]}
    labels = {28:'Ni',27:'Co',22:'Ti',40:'Zr',72:'Hf'}
    colors = {28:'red',27:'blue',22:'green',40:'orange',72:'purple'}

    plt.figure(figsize=(12, 6))
    plt.suptitle(title, fontsize=14)

    # 主要元素 (Ni, Co)
    ax1 = plt.subplot(1,2,1)
    ax1.plot(top_ns, ratios[28], 'o-', color=colors[28], label=labels[28], linewidth=2, markersize=6)
    ax1.plot(top_ns, ratios[27], 's-', color=colors[27], label=labels[27], linewidth=2, markersize=6)
    ax1.axhline(0.25, linestyle='--', color='gray', alpha=0.7, label='y=0.25')
    ax1.set_ylabel('Element Ratio')
    ax1.set_title('Ni & Co Ratio vs Top-N')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xlabel('Top-N (Number of High-Strain Atoms)')

    # 次要元素 (Ti, Zr, Hf)
    ax2 = plt.subplot(1,2,2)
    ax2.plot(top_ns, ratios[22], '^-', color=colors[22], label=labels[22], linewidth=2, markersize=6)
    ax2.plot(top_ns, ratios[40], 'd-', color=colors[40], label=labels[40], linewidth=2, markersize=6)
    ax2.plot(top_ns, ratios[72], 'v-', color=colors[72], label=labels[72], linewidth=2, markersize=6)
    ax2.axhline(0.5/3.0, linestyle='--', color='gray', alpha=0.7, label='y=0.5/3')
    ax2.set_xlabel('Top-N (Number of High-Strain Atoms)')
    ax2.set_ylabel('Element Ratio')
    ax2.set_title('Ti, Zr & Hf Ratio vs Top-N')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_plot, dpi=300, bbox_inches='tight')
    plt.close()


def process_case(input_file, ref_file, prefix, rcut=3.0):
    title = f"{prefix} chemical composition analysis"
    
    # 執行多個top_n值的分析 (100到1000，步長100)
    top_n_values = list(range(100, 1001, 100))  # [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    all_results = []
    
    for top_n in top_n_values:
        print(f"Processing {prefix} with top_n={top_n}, rcut={rcut}")
        results = rcut_parameter_scan(input_file, ref_file, top_n=top_n, rcut=rcut)
        all_results.extend(results)
    
    # 儲存所有結果到CSV
    csv_file = f"{prefix}_rcut_{rcut}_multi_topn.csv"
    keys = ['rcut','count','top_n'] + [f"ratio_{z}" for z in [28,27,22,40,72]]
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(all_results)
    
    print(f"Results saved to: {csv_file}")
    
    # 生成top_n vs 元素比例的圖表
    plot_topn_analysis(all_results, f"{prefix}_rcut_{rcut}_topn_analysis.png", f"{prefix} Top-N Analysis (rcut={rcut})")

    # 新增：分析中心區域應變前200大的原子構成
    center_result = analyze_center_strain_atoms(input_file, ref_file, z_range=25.0)
    print_center_analysis(center_result, prefix)
    
    # 儲存中心分析結果到CSV
    center_csv_file = f"{prefix}_center_analysis.csv"
    center_keys = ['total_atoms', 'z_center', 'z_range', 'z_min', 'z_max'] + [f"ratio_{z}" for z in [28,27,22,40,72]]
    with open(center_csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=center_keys)
        writer.writeheader()
        writer.writerow(center_result)

    print(f"Completed {prefix}")


def analyze_center_strain_atoms(input_file, ref_file, z_range=25.0):
    """
    取出應變前200大的原子，並只分析z距離正中心±z_range範圍內的原子構成
    
    Args:
        input_file: 輸入的LAMMPS data檔案
        ref_file: 參考的LAMMPS data檔案
        z_range: z方向中心範圍 (Å)
    
    Returns:
        dict: 包含原子數量和元素比例的字典
    """
    # 獲取應變前200大的原子位置
    points = get_top_strain_points(input_file, ref_file, top_n=500)
    
    # 讀取原子資料
    ztype = {1:28, 2:27, 3:22, 4:40, 5:72}
    atoms = read_lammps_data(input_file, atom_style='atomic', Z_of_type=ztype)
    positions = atoms.get_positions()
    numbers = atoms.get_atomic_numbers()
    
    # 計算z方向的中心
    z_vals = positions[:, 2]
    z_center = (z_vals.min() + z_vals.max()) / 2.0
    
    # 篩選在z中心±z_range範圍內的原子
    z_mask = (z_vals >= z_center - z_range) & (z_vals <= z_center + z_range)
    
    # 找出應變前200大的原子中，在z範圍內的原子
    center_atom_ids = []
    for point in points:
        # 找到最接近的原子
        distances = np.linalg.norm(positions - point, axis=1)
        closest_id = np.argmin(distances)
        
        # 檢查該原子是否在z範圍內
        if z_mask[closest_id]:
            center_atom_ids.append(closest_id)
    
    # 去重
    center_atom_ids = list(set(center_atom_ids))
    
    # 計算元素比例
    ratios = calculate_element_ratios(center_atom_ids, numbers)
    
    # 準備結果
    result = {
        'total_atoms': len(center_atom_ids),
        'z_center': z_center,
        'z_range': z_range,
        'z_min': z_center - z_range,
        'z_max': z_center + z_range,
        **{f"ratio_{z}": ratios[z] for z in sorted(ratios)}
    }
    
    return result


def print_center_analysis(result, prefix):
    """
    印出中心區域分析結果
    
    Args:
        result: analyze_center_strain_atoms的結果
        prefix: 檔案前綴
    """
    labels = {28: 'Ni', 27: 'Co', 22: 'Ti', 40: 'Zr', 72: 'Hf'}
    
    print(f"\n=== {prefix} 中心區域應變分析 ===")
    print(f"Z中心: {result['z_center']:.2f} Å")
    print(f"Z範圍: {result['z_min']:.2f} ~ {result['z_max']:.2f} Å")
    print(f"符合條件的原子數: {result['total_atoms']}")
    print("\n元素比例:")
    for z in sorted([28, 27, 22, 40, 72]):
        ratio = result[f'ratio_{z}']
        print(f"  {labels[z]}: {ratio:.4f} ({ratio*100:.2f}%)")


def calculate_warren_cowley_parameters_ovito(input_file, atom_ids=None, nneigh=[0, 8, 14]):
    """
    使用OVITO的WarrenCowleyParameters模組計算Warren-Cowley參數
    
    Args:
        input_file: 輸入的LAMMPS data檔案
        atom_ids: 要分析的原子ID列表（None表示分析所有原子）
        nneigh: 鄰居殼層設定 [0, 12, 18] 表示1NN和2NN
    
    Returns:
        dict: 包含各殼層Warren-Cowley參數的字典
    """
    try:
        import WarrenCowleyParameters as wc
    except ImportError:
        print("警告: 無法導入WarrenCowleyParameters模組，請確保已安裝")
        return {}
    
    # 創建pipeline
    pipeline = import_file(input_file)
    
    # 如果指定了原子ID，創建選擇集
    if atom_ids is not None:
        from ovito.modifiers import ExpressionSelectionModifier
        # 創建選擇表達式 - 使用OR邏輯
        conditions = []
        for atom_id in atom_ids:
            conditions.append(f"ParticleIndex == {atom_id}")
        selection_expr = " || ".join(conditions)
        select_mod = ExpressionSelectionModifier(expression=selection_expr)
        pipeline.modifiers.append(select_mod)
    
    # 添加Warren-Cowley參數計算器
    mod = wc.WarrenCowleyParameters(nneigh=nneigh, only_selected=True)
    pipeline.modifiers.append(mod)
    
    # 計算
    data = pipeline.compute()
    
    # 獲取結果
    wc_for_shells = data.attributes["Warren-Cowley parameters"]
    wc_by_name = data.attributes["Warren-Cowley parameters by particle name"]
    
    # 整理結果
    result = {
        'shells': wc_for_shells,
        'by_name': wc_by_name
    }
    
    # 如果指定了原子ID，也獲取每個原子的參數
    if atom_ids is not None:
        per_particle_data = {}
        for i, shell in enumerate(nneigh[1:], 1):  # 跳過0，從1開始
            attr_name = f"Warren-Cowley parameter (shell={i})"
            if attr_name in data.particles:
                per_particle_data[f'shell_{i}'] = data.particles[attr_name][...]
        result['per_particle'] = per_particle_data
    
    return result


def print_warren_cowley_analysis_ovito(wc_result, prefix):
    """
    印出OVITO Warren-Cowley參數分析結果
    
    Args:
        wc_result: OVITO Warren-Cowley參數結果
        prefix: 檔案前綴
    """
    # 元素映射
    element_labels = {28: 'Ni', 27: 'Co', 22: 'Ti', 40: 'Zr', 72: 'Hf'}
    
    print(f"\n=== {prefix} Warren-Cowley參數分析 (OVITO) ===")
    print("正值表示偏聚，負值表示分離，0表示隨機分布")
    print()
    
    # 印出各殼層的參數
    if 'shells' in wc_result:
        shells = wc_result['shells']
        for i, shell_matrix in enumerate(shells):
            print(f"--- {i+1}NN Warren-Cowley參數 ---")
            # 創建帶有元素標籤的矩陣
            n_elements = shell_matrix.shape[0]
            element_names = [element_labels.get(28, 'Ni'), element_labels.get(27, 'Co'), 
                           element_labels.get(22, 'Ti'), element_labels.get(40, 'Zr'), 
                           element_labels.get(72, 'Hf')][:n_elements]
            
            # 印出列標題
            header = "      " + " ".join(f"{name:>8}" for name in element_names)
            print(header)
            
            # 印出矩陣內容
            for row_idx, row in enumerate(shell_matrix):
                row_name = element_names[row_idx]
                row_str = f"{row_name:>6} " + " ".join(f"{val:>8.6f}" for val in row)
                print(row_str)
            print()
    
    # 印出按元素名稱的參數
    if 'by_name' in wc_result:
        print("--- 按元素名稱的Warren-Cowley參數 ---")
        by_name = wc_result['by_name']
        if isinstance(by_name, dict):
            for element_pair, value in by_name.items():
                print(f"{element_pair}: {value:.6f}")
        elif isinstance(by_name, list):
            for i, value in enumerate(by_name):
                if isinstance(value, dict):
                    print(f"Element_{i}:")
                    for k, v in value.items():
                        print(f"  {k}: {v:.6f}")
                else:
                    print(f"Element_{i}: {value:.6f}")
        print()
    
    # 如果有多個原子的個別參數，印出統計
    if 'per_particle' in wc_result:
        per_particle = wc_result['per_particle']
        for shell_name, particle_data in per_particle.items():
            print(f"--- {shell_name} 個別原子參數統計 ---")
            print(f"平均值: {np.mean(particle_data):.6f}")
            print(f"標準差: {np.std(particle_data):.6f}")
            print(f"最小值: {np.min(particle_data):.6f}")
            print(f"最大值: {np.max(particle_data):.6f}")
            print()


def analyze_warren_cowley_case(input_file, ref_file, prefix, z_range=25.0, nneigh=[0, 14, 28]):
    """
    第二個case: 使用OVITO計算中心區域應變原子的Warren-Cowley參數
    
    Args:
        input_file: 輸入的LAMMPS data檔案
        ref_file: 參考的LAMMPS data檔案
        prefix: 檔案前綴
        z_range: z方向中心範圍 (Å)
        nneigh: 鄰居殼層設定 [0, 12, 18] 表示1NN和2NN
    """
    print(f"\n開始Warren-Cowley分析 (OVITO): {prefix}")
    
    # 獲取應變前200大的原子位置
    points = get_top_strain_points(input_file, ref_file, top_n=1000)
    
    # 讀取原子資料
    ztype = {1:28, 2:27, 3:22, 4:40, 5:72}
    atoms = read_lammps_data(input_file, atom_style='atomic', Z_of_type=ztype)
    positions = atoms.get_positions()
    numbers = atoms.get_atomic_numbers()
    
    # 計算z方向的中心
    z_vals = positions[:, 2]
    z_center = (z_vals.min() + z_vals.max()) / 2.0
    
    # 篩選在z中心±z_range範圍內的原子
    z_mask = (z_vals >= z_center - z_range) & (z_vals <= z_center + z_range)
    
    # 找出應變前200大的原子中，在z範圍內的原子
    center_atom_ids = []
    for point in points:
        # 找到最接近的原子
        distances = np.linalg.norm(positions - point, axis=1)
        closest_id = np.argmin(distances)
        
        # 檢查該原子是否在z範圍內
        if z_mask[closest_id]:
            center_atom_ids.append(closest_id)
    
    # 去重
    center_atom_ids = list(set(center_atom_ids))
    
    print(f"分析原子數量: {len(center_atom_ids)}")
    print(f"Z中心: {z_center:.2f} Å")
    print(f"Z範圍: {z_center - z_range:.2f} ~ {z_center + z_range:.2f} Å")
    print(f"鄰居殼層設定: {nneigh}")
    
    # 使用OVITO計算Warren-Cowley參數
    wc_result = calculate_warren_cowley_parameters_ovito(input_file, center_atom_ids, nneigh)
    
    if not wc_result:
        print("Warren-Cowley參數計算失敗")
        return
    
    # 印出結果
    print_warren_cowley_analysis_ovito(wc_result, prefix)
    
    # 儲存結果到CSV
    wc_csv_file = f"{prefix}_warren_cowley_ovito.csv"
    with open(wc_csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # 元素映射
        element_labels = {28: 'Ni', 27: 'Co', 22: 'Ti', 40: 'Zr', 72: 'Hf'}
        
        # 寫入殼層參數
        if 'shells' in wc_result:
            writer.writerow(['Shell Parameters'])
            for i, shell_matrix in enumerate(wc_result['shells']):
                writer.writerow([f'{i+1}NN'])
                # 創建元素標籤
                n_elements = shell_matrix.shape[0]
                element_names = [element_labels.get(28, 'Ni'), element_labels.get(27, 'Co'), 
                               element_labels.get(22, 'Ti'), element_labels.get(40, 'Zr'), 
                               element_labels.get(72, 'Hf')][:n_elements]
                
                writer.writerow([''] + element_names)
                for row_idx, row in enumerate(shell_matrix):
                    row_name = element_names[row_idx]
                    writer.writerow([row_name] + [f'{val:.6f}' for val in row])
                writer.writerow([])
        
        # 寫入按元素名稱的參數
        if 'by_name' in wc_result:
            writer.writerow(['Element Pair Parameters'])
            by_name = wc_result['by_name']
            if isinstance(by_name, dict):
                for element_pair, value in by_name.items():
                    writer.writerow([element_pair, f'{value:.6f}'])
            elif isinstance(by_name, list):
                for i, value in enumerate(by_name):
                    if isinstance(value, dict):
                        writer.writerow([f'Element_{i}'])
                        for k, v in value.items():
                            writer.writerow([f'  {k}', f'{v:.6f}'])
                    else:
                        writer.writerow([f'Element_{i}', f'{value:.6f}'])
            writer.writerow([])
        
        # 寫入個別原子參數統計
        if 'per_particle' in wc_result:
            writer.writerow(['Per-Particle Statistics'])
            for shell_name, particle_data in wc_result['per_particle'].items():
                writer.writerow([shell_name])
                writer.writerow(['Mean', 'Std', 'Min', 'Max'])
                writer.writerow([
                    f'{np.mean(particle_data):.6f}',
                    f'{np.std(particle_data):.6f}',
                    f'{np.min(particle_data):.6f}',
                    f'{np.max(particle_data):.6f}'
                ])
                writer.writerow([])
    
    print(f"Warren-Cowley參數已儲存至: {wc_csv_file}")


def analyze_center_atoms_rcut_scan(input_file, ref_file, prefix, z_range=25.0, rcut_range=(0.0,12.0), rcut_step=0.2):
    """
    第三個case: 計算中心區域應變原子周圍rcut從3-12Å的原子比例並畫圖
    
    Args:
        input_file: 輸入的LAMMPS data檔案
        ref_file: 參考的LAMMPS data檔案
        prefix: 檔案前綴
        z_range: z方向中心範圍 (Å)
        rcut_range: rcut範圍 (min, max)
        rcut_step: rcut步長
    """
    print(f"\n開始中心原子rcut掃描分析: {prefix}")
    
    # 獲取應變前200大的原子位置
    points = get_top_strain_points(input_file, ref_file, top_n=200)
    
    # 讀取原子資料
    ztype = {1:28, 2:27, 3:22, 4:40, 5:72}
    atoms = read_lammps_data(input_file, atom_style='atomic', Z_of_type=ztype)
    positions = atoms.get_positions()
    numbers = atoms.get_atomic_numbers()
    cell = np.array(atoms.cell.cellpar()[:3])
    
    # 計算z方向的中心
    z_vals = positions[:, 2]
    z_center = (z_vals.min() + z_vals.max()) / 2.0
    
    # 篩選在z中心±z_range範圍內的原子
    z_mask = (z_vals >= z_center - z_range) & (z_vals <= z_center + z_range)
    
    # 找出應變前200大的原子中，在z範圍內的原子
    center_atom_ids = []
    for point in points:
        # 找到最接近的原子
        distances = np.linalg.norm(positions - point, axis=1)
        closest_id = np.argmin(distances)
        
        # 檢查該原子是否在z範圍內
        if z_mask[closest_id]:
            center_atom_ids.append(closest_id)
    
    # 去重
    center_atom_ids = list(set(center_atom_ids))
    
    print(f"分析原子數量: {len(center_atom_ids)}")
    print(f"Z中心: {z_center:.2f} Å")
    print(f"Z範圍: {z_center - z_range:.2f} ~ {z_center + z_range:.2f} Å")
    print(f"rcut範圍: {rcut_range[0]:.1f} ~ {rcut_range[1]:.1f} Å")
    
    # 對每個rcut值計算原子比例
    results = []
    rcuts = np.arange(rcut_range[0], rcut_range[1] + rcut_step, rcut_step)
    
    for r in rcuts:
        # 獲取中心原子周圍rcut範圍內的所有原子
        surrounding_atom_ids = get_atoms_near_points(
            positions[center_atom_ids], positions, cell, r
        )
        
        # 計算元素比例
        ratios = calculate_element_ratios(surrounding_atom_ids, numbers)
        
        results.append({
            'rcut': r,
            'count': len(surrounding_atom_ids),
            **{f"ratio_{z}": ratios[z] for z in sorted(ratios)}
        })
    
    # 印出結果摘要
    print(f"\n=== {prefix} 中心原子rcut掃描分析 ===")
    print(f"rcut掃描範圍: {rcut_range[0]:.1f} ~ {rcut_range[1]:.1f} Å")
    print(f"掃描點數: {len(results)}")
    
    # 畫圖
    plot_center_atoms_rcut_scan(results, f"{prefix}_center_rcut_scan.png", f"{prefix} Center Atoms Rcut Scan Analysis")
    
    # 儲存結果到CSV
    csv_file = f"{prefix}_center_rcut_scan.csv"
    keys = ['rcut', 'count'] + [f"ratio_{z}" for z in [28, 27, 22, 40, 72]]
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"結果已儲存至: {csv_file}")
    print(f"圖表已儲存至: {prefix}_center_rcut_scan.png")


def plot_center_atoms_rcut_scan(results, output_plot, title):
    """
    Plot center atoms rcut scan results
    
    Args:
        results: rcut scan results
        output_plot: output plot filename
        title: plot title
    """
    import matplotlib.pyplot as plt
    
    rcuts = [r['rcut'] for r in results]
    counts = [r['count'] for r in results]
    ratios = {z: [r[f"ratio_{z}"] for r in results] for z in [28, 27, 22, 40, 72]}
    labels = {28: 'Ni', 27: 'Co', 22: 'Ti', 40: 'Zr', 72: 'Hf'}
    
    # Create subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    fig.suptitle(title, fontsize=14)
    
    # Atom count plot
    ax1.plot(rcuts, counts, 'b-', linewidth=2, label='Atom Count')
    ax1.set_ylabel('Atom Count')
    ax1.set_title('Atom Count around Center Atoms vs rcut')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Element ratio plot
    colors = ['red', 'blue', 'green', 'orange', 'purple']
    for i, z in enumerate([28, 27, 22, 40, 72]):
        ax2.plot(rcuts, ratios[z], color=colors[i], linewidth=2, label=labels[z])
    
    # Add reference lines
    ax2.axhline(0.25, linestyle='--', color='gray', alpha=0.7, label='y=0.25 (Ni/Co Expected)')
    ax2.axhline(0.5/3.0, linestyle=':', color='gray', alpha=0.7, label='y=0.167 (Ti/Zr/Hf Expected)')
    
    ax2.set_xlabel('rcut (Å)')
    ax2.set_ylabel('Element Ratio')
    ax2.set_title('Element Ratio around Center Atoms vs rcut')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig(output_plot, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Plot saved: {output_plot}")


def main():
    cases = [
        ("edge_b100_p100_NEB/next3/HEA_opt_edge1.data", "edge_b100_p100_NEB/HEA_init_edge1.data", "b100p100_edge"),
        ("edge_b100_p110_NEB/next5/HEA_opt_edge1.data", "edge_b100_p110_NEB/HEA_init_edge1.data", "b100p110_edge"),
        ("edge_b110_p110_NEB/next3/HEA_opt_edge1.data", "edge_b110_p110_NEB/HEA_init_edge1.data", "b110p110_edge"),
        ("edge_b111_p110_NEB/next3/HEA_opt_edge1.data", "edge_b111_p110_NEB/HEA_init_edge1.data", "b111p110_edge"),
        ("screw_b100_p100_NEB/next5/HEA_opt_screw1.data", "screw_b100_p100_NEB/HEA_init_screw1.data", "b100p100_screw"),
        ("screw_b100_p110_NEB/use/screw_b100_p110_NEB/next2/HEA_opt_screw1.data", "screw_b100_p110_NEB/HEA_init_screw1.data", "b100p110_screw"),
        ("screw_b110_p110_NEB/use/screw_b110_p110_NEB/next5/HEA_opt_screw1.data", "screw_b110_p110_NEB/HEA_init_screw1.data", "b110p110_screw"),
        ("screw_b111_p110_NEB/next1/HEA_opt_screw1.data", "screw_b111_p110_NEB/HEA_init_screw1.data", "b111p110_screw"),
    ]
    base = "dislocation/practice_dislocation/v3_trial3/NEB_new"

    # 檢查命令行參數來決定執行哪個case
    if len(sys.argv) == 1:
        # 預設執行第一個case，使用預設rcut=3.0
        for subdir_in, subdir_ref, prefix in cases:
            input_path = os.path.join(base, subdir_in)
            ref_path = os.path.join(base, subdir_ref)
            print("start", prefix)
            process_case(input_path, ref_path, prefix, rcut=3.0)
    elif len(sys.argv) == 2 and sys.argv[1].startswith("rcut="):
        # 使用指定的rcut值執行第一個case
        try:
            rcut_value = float(sys.argv[1].split("=")[1])
            print(f"Using rcut={rcut_value}")
            for subdir_in, subdir_ref, prefix in cases:
                input_path = os.path.join(base, subdir_in)
                ref_path = os.path.join(base, subdir_ref)
                print("start", prefix)
                process_case(input_path, ref_path, prefix, rcut=rcut_value)
        except (ValueError, IndexError):
            print("Error: Invalid rcut format. Use 'rcut=3.5' for example.")
            sys.exit(1)
    elif len(sys.argv) == 2 and sys.argv[1] == "warren_cowley":
        # 執行所有案例的Warren-Cowley分析
        for subdir_in, subdir_ref, prefix in cases:
            input_path = os.path.join(base, subdir_in)
            ref_path = os.path.join(base, subdir_ref)
            print("start", prefix)
            analyze_warren_cowley_case(input_path, ref_path, prefix)
    elif len(sys.argv) == 2 and sys.argv[1] == "center_rcut":
        # 執行所有案例的中心原子rcut掃描分析
        for subdir_in, subdir_ref, prefix in cases:
            input_path = os.path.join(base, subdir_in)
            ref_path = os.path.join(base, subdir_ref)
            print("start", prefix)
            analyze_center_atoms_rcut_scan(input_path, ref_path, prefix)
    elif len(sys.argv) >= 4:
        infile, ref, prefix = sys.argv[1:4]
        rcut = 3.0  # 預設rcut值
        if len(sys.argv) >= 5:
            if sys.argv[4] == "warren_cowley":
                # 第二個case: Warren-Cowley參數分析
                analyze_warren_cowley_case(infile, ref, prefix)
            elif sys.argv[4] == "center_rcut":
                # 第三個case: 中心原子rcut掃描分析
                analyze_center_atoms_rcut_scan(infile, ref, prefix)
            elif sys.argv[4].startswith("rcut="):
                # 使用指定的rcut值
                try:
                    rcut = float(sys.argv[4].split("=")[1])
                    print(f"Using rcut={rcut}")
                    process_case(infile, ref, prefix, rcut=rcut)
                except (ValueError, IndexError):
                    print("Error: Invalid rcut format. Use 'rcut=3.5' for example.")
                    sys.exit(1)
            else:
                # 第一個case: 原有的分析
                process_case(infile, ref, prefix, rcut=rcut)
        else:
            # 第一個case: 原有的分析
            process_case(infile, ref, prefix, rcut=rcut)
    else:
        print("使用方法:")
        print("  python strain_scan.py                                    # 執行所有案例的第一個case (rcut=3.0)")
        print("  python strain_scan.py rcut=3.5                           # 執行所有案例的第一個case (自訂rcut)")
        print("  python strain_scan.py warren_cowley                      # 執行所有案例的Warren-Cowley分析")
        print("  python strain_scan.py center_rcut                        # 執行所有案例的中心原子rcut掃描分析")
        print("  python strain_scan.py input.data ref.data prefix        # 執行單一案例的第一個case (rcut=3.0)")
        print("  python strain_scan.py input.data ref.data prefix rcut=3.5  # 執行單一案例的第一個case (自訂rcut)")
        print("  python strain_scan.py input.data ref.data prefix warren_cowley  # 執行單一案例的Warren-Cowley分析")
        print("  python strain_scan.py input.data ref.data prefix center_rcut    # 執行單一案例的中心原子rcut掃描分析")

if __name__ == '__main__':
    main()
