import os
import numpy as np
import ase.io
from ase.io.lammpsdata import read_lammps_data
import math
from operator import itemgetter
from ovito.io import import_file, export_file
from ovito.modifiers import DislocationAnalysisModifier
from ovito.data import DislocationNetwork
import csv


def get_dislocation(filename):
    pipeline = import_file(filename)
    modifier = DislocationAnalysisModifier()
    modifier.input_crystal_structure = DislocationAnalysisModifier.Lattice.BCC
    modifier.defect_mesh_smoothing_level = 10
    modifier.trial_circuit_length = 80
    modifier.circuit_stretchability = 10
    modifier.line_point_separation = 0.5
    pipeline.modifiers.append(modifier)
    data = pipeline.compute()
    linepoints = []
    for segment in data.dislocations.segments:
        for i in range(len(segment.points)):
            linepoints.append([segment.points[i][0],segment.points[i][1],segment.points[i][2]])

    linepoints = np.array(linepoints)
    list_x = linepoints[:,0]
    max_x = np.max(list_x)
    min_x = np.min(list_x)
    max_id = np.argmax(list_x)
    min_id = np.argmin(list_x)
    ### find the first fastest and slowest linepoints ###
    fast_pid = []
    slow_pid = []
    for i in range(3):
        fid = max_id-i-1
        if fid < 0:
            fid = len(linepoints)+fid
        elif fid > len(linepoints)-1:
            fid = fid-len(linepoints)
        fast_pid.append(fid)
        sid = min_id-i-1
        if sid < 0:
            sid = len(linepoints)+sid
        elif sid > len(linepoints)-1:
            sid = sid-len(linepoints)
        slow_pid.append(sid)
    return linepoints, fast_pid, slow_pid


def get_dist(atom_pos, line_pos, cell):
    lenx = cell[0]
    leny = cell[1]
    lenz = cell[2]
    dispx = atom_pos[0]-line_pos[0]
    if dispx > 0.5*lenx: dispx -= lenx
    if dispx < -0.5*lenx: dispx += lenx
    dispy = atom_pos[1]-line_pos[1]
    if dispy > 0.5*leny: dispy -= leny
    if dispy < -0.5*leny: dispy += leny
    dispz = atom_pos[2]-line_pos[2]
    if dispz > 0.5*lenz: dispz -= lenz
    if dispz < -0.5*lenz: dispz += lenz
    dist = math.sqrt(dispx**2 + dispy**2 + dispz**2)
    return dist


def get_atoms_near_points(point_list, pos, cell, rcut):
    """
    獲取指定點附近的原子
    """
    atom_ids = []
    for point in point_list:
        for i in range(len(pos)):
            atom_pos = pos[i]
            dist = get_dist(atom_pos, point, cell)
            if dist <= rcut:
                atom_ids.append(i)
    
    return list(set(atom_ids))  # 去除重複


def calculate_element_ratios(atom_ids, atomic_number):
    """
    計算元素Ratio
    """
    if len(atom_ids) == 0:
        return {28: 0, 27: 0, 22: 0, 40: 0, 72: 0}
    
    element_counts = {28: 0, 27: 0, 22: 0, 40: 0, 72: 0}  # Ni, Co, Ti, Zr, Hf
    
    for atom_id in atom_ids:
        elem = atomic_number[atom_id]
        if elem in element_counts:
            element_counts[elem] += 1
    
    total_atoms = len(atom_ids)
    element_ratios = {elem: count/total_atoms for elem, count in element_counts.items()}
    
    return element_ratios


def rcut_parameter_scan(filename, output_file="rcut_analysis.csv"):
    """
    掃描不同 rcut 值的影響
    """
    print("="*60)
    print("RCUT 參數掃描分析")
    print("="*60)
    
    # 讀取數據
    linepoints, fast_pid, slow_pid = get_dislocation(filename)
    ztype = {1:28, 2:27, 3:22, 4:40, 5:72}
    atoms = read_lammps_data(filename, atom_style="atomic", Z_of_type=ztype)
    pos = atoms.get_positions()
    atomic_number = atoms.get_atomic_numbers()
    natoms = len(atoms)
    cell = atoms.cell.cellpar()
    
    print(f"系統信息：")
    print(f"總原子數: {natoms}")
    print(f"晶胞大小: {cell[0]:.2f} × {cell[1]:.2f} × {cell[2]:.2f} Å³")
    print(f"位錯線點數: {len(linepoints)}")
    
    # 獲取位錯點座標
    fast_points = [linepoints[pid] for pid in fast_pid]
    slow_points = [linepoints[pid] for pid in slow_pid]
    
    print(f"Fast dislocation points: {len(fast_points)}")
    print(f"Slow dislocation points: {len(slow_points)}")
    
    # 元素名稱映射
    element_names = {28: 'Ni', 27: 'Co', 22: 'Ti', 40: 'Zr', 72: 'Hf'}
    
    # 準備輸出數據
    results = []
    
    # rcut 從 3.0 到 8.0，步長 0.1
    rcut_values = np.arange(3.0, 12.1, 0.1)
    
    print(f"\n開始掃描 rcut 值從 {rcut_values[0]:.1f} 到 {rcut_values[-1]:.1f} Å...")
    
    for i, rcut in enumerate(rcut_values):
        if i % 10 == 0:
            print(f"進度: {i/len(rcut_values)*100:.1f}% (rcut = {rcut:.1f} Å)")
        
        # 獲取各區域的原子
        fast_atoms = get_atoms_near_points(fast_points, pos, cell, rcut)
        slow_atoms = get_atoms_near_points(slow_points, pos, cell, rcut)
        
        # 計算元素Ratio
        fast_ratios = calculate_element_ratios(fast_atoms, atomic_number)
        slow_ratios = calculate_element_ratios(slow_atoms, atomic_number)
        
        # 記錄結果
        result = {
            'rcut': rcut,
            'fast_count': len(fast_atoms),
            'slow_count': len(slow_atoms),
            'fast_Ni': fast_ratios[28],
            'fast_Co': fast_ratios[27],
            'fast_Ti': fast_ratios[22],
            'fast_Zr': fast_ratios[40],
            'fast_Hf': fast_ratios[72],
            'slow_Ni': slow_ratios[28],
            'slow_Co': slow_ratios[27],
            'slow_Ti': slow_ratios[22],
            'slow_Zr': slow_ratios[40],
            'slow_Hf': slow_ratios[72]
        }
        
        results.append(result)
    
    # 輸出到 CSV 文件
    print(f"\n將結果寫入 {output_file}...")
    
    fieldnames = [
        'rcut', 'fast_count', 'slow_count',
        'fast_Ni', 'fast_Co', 'fast_Ti', 'fast_Zr', 'fast_Hf',
        'slow_Ni', 'slow_Co', 'slow_Ti', 'slow_Zr', 'slow_Hf'
    ]
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"結果已保存到 {output_file}")
    
    # 打印總結統計
    print("\n" + "="*60)
    print("總結統計")
    print("="*60)
    
    # 選擇幾個代表性的 rcut 值來顯示
    display_rcuts = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    
    print(f"{'rcut':>5} | {'Fast':>6} | {'Slow':>6} | 說明")
    print("-" * 35)
    
    for rcut in display_rcuts:
        # 找到最接近的 rcut 值
        idx = np.argmin(np.abs(rcut_values - rcut))
        result = results[idx]
        
        fast_count = result['fast_count']
        slow_count = result['slow_count']
        
        description = ""
        if rcut <= 3.5:
            description = "核心區域"
        elif rcut <= 5.0:
            description = "近場影響"
        elif rcut <= 7.0:
            description = "中場影響"
        else:
            description = "遠場影響"
        
        print(f"{rcut:5.1f} | {fast_count:6d} | {slow_count:6d} | {description}")
    
    return results


def plot_rcut_analysis(results, output_plot="rcut_analysis.png"):
    """
    繪製 rcut 分析結果圖表（可選功能）
    """
    try:
        import matplotlib.pyplot as plt
        
        rcuts = [r['rcut'] for r in results]
        fast_counts = [r['fast_count'] for r in results]
        slow_counts = [r['slow_count'] for r in results]
        
        plt.figure(figsize=(15, 10))
        
        # 原子數量變化
        plt.subplot(2, 3, 1)
        plt.plot(rcuts, fast_counts, 'r-', label='Fast dislocation', linewidth=2)
        plt.plot(rcuts, slow_counts, 'b-', label='Slow dislocation', linewidth=2)
        plt.xlabel('rcut (Å)')
        plt.ylabel('Atoms number')
        plt.title('Atoms number vs rcut')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Ni Ratio變化
        plt.subplot(2, 3, 2)
        fast_ni = [r['fast_Ni'] for r in results]
        slow_ni = [r['slow_Ni'] for r in results]
        plt.plot(rcuts, fast_ni, 'r-', label='Fast', linewidth=2)
        plt.plot(rcuts, slow_ni, 'b-', label='Slow', linewidth=2)
        plt.xlabel('rcut (Å)')
        plt.ylabel('Ni Ratio')
        plt.title('Ni Ratio vs rcut')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Co Ratio變化
        plt.subplot(2, 3, 3)
        fast_co = [r['fast_Co'] for r in results]
        slow_co = [r['slow_Co'] for r in results]
        plt.plot(rcuts, fast_co, 'r-', label='Fast', linewidth=2)
        plt.plot(rcuts, slow_co, 'b-', label='Slow', linewidth=2)
        plt.xlabel('rcut (Å)')
        plt.ylabel('Co Ratio')
        plt.title('Co Ratio vs rcut')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Ti Ratio變化
        plt.subplot(2, 3, 4)
        fast_ti = [r['fast_Ti'] for r in results]
        slow_ti = [r['slow_Ti'] for r in results]
        plt.plot(rcuts, fast_ti, 'r-', label='Fast', linewidth=2)
        plt.plot(rcuts, slow_ti, 'b-', label='Slow', linewidth=2)
        plt.xlabel('rcut (Å)')
        plt.ylabel('Ti Ratio')
        plt.title('Ti Ratio vs rcut')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Zr Ratio變化
        plt.subplot(2, 3, 5)
        fast_zr = [r['fast_Zr'] for r in results]
        slow_zr = [r['slow_Zr'] for r in results]
        plt.plot(rcuts, fast_zr, 'r-', label='Fast', linewidth=2)
        plt.plot(rcuts, slow_zr, 'b-', label='Slow', linewidth=2)
        plt.xlabel('rcut (Å)')
        plt.ylabel('Zr Ratio')
        plt.title('Zr Ratio vs rcut')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Hf Ratio變化
        plt.subplot(2, 3, 6)
        fast_hf = [r['fast_Hf'] for r in results]
        slow_hf = [r['slow_Hf'] for r in results]
        plt.plot(rcuts, fast_hf, 'r-', label='Fast', linewidth=2)
        plt.plot(rcuts, slow_hf, 'b-', label='Slow', linewidth=2)
        plt.xlabel('rcut (Å)')
        plt.ylabel('Hf Ratio')
        plt.title('Hf Ratio vs rcut')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_plot, dpi=300, bbox_inches='tight')
        plt.show()
        print(f"圖表已保存到 {output_plot}")
        
    except ImportError:
        print("matplotlib 未安裝，跳過圖表生成")


# 主程式
if __name__ == "__main__":
    # 滑移系配置
    slip_systems = {
        # "edge_b100_p100_NEB": {
        #     "next": 1,
        #     "neb_numbers": [4, 6, 10]  # 可以根據需要修改
        # },
        # "edge_b100_p110_NEB": {
        #     "next": 5,
        #     "neb_numbers": [5, 7, 10]  # 可以根據需要修改
        # },
        "edge_b111_p110_NEB": {
            "next": 2,
            "neb_numbers": [3, 7, 9]  # 可以根據需要修改
        }
    }
    
    base_path = "dislocation/practice_dislocation/v3_trial3/NEB_new"
    
    print("="*80)
    print("開始多滑移系 rcut 參數掃描分析")
    print("="*80)
    
    # 遍歷每個滑移系
    for slip_system, config in slip_systems.items():
        print(f"\n{'='*60}")
        print(f"正在分析滑移系: {slip_system}")
        print(f"Next值: {config['next']}, NEB編號: {config['neb_numbers']}")
        print(f"{'='*60}")
        
        # 遍歷每個 NEB 編號
        for neb_num in config['neb_numbers']:
            print(f"\n處理 {slip_system} - NEB {neb_num}...")
            
            # 構建文件路徑
            file_path = f"{base_path}/{slip_system}/large/next{config['next']}/neb_{neb_num}.data"
            
            # 生成輸出文件名
            csv_output = f"rcut_analysis_{slip_system}_neb{neb_num}.csv"
            png_output = f"rcut_analysis_{slip_system}_neb{neb_num}.png"
            
            try:
                # 執行 rcut 掃描分析
                print(f"  - 讀取文件: {file_path}")
                results = rcut_parameter_scan(file_path, csv_output)
                
                # 生成圖表
                plot_rcut_analysis(results, png_output)
                
                print(f"  ✓ 完成分析")
                print(f"    - CSV: {csv_output}")
                print(f"    - PNG: {png_output}")
                    
            except FileNotFoundError:
                print(f"  ✗ 文件不存在: {file_path}")
            except Exception as e:
                print(f"  ✗ 分析失敗: {str(e)}")
    
    print("\n" + "="*80)
    print("所有滑移系分析完成！")
    print("="*80)
    print("輸出文件總覽：")
    
    # 列出所有預期的輸出文件
    for slip_system, config in slip_systems.items():
        print(f"\n{slip_system}:")
        for neb_num in config['neb_numbers']:
            print(f"  - rcut_analysis_{slip_system}_neb{neb_num}.csv")
            print(f"  - rcut_analysis_{slip_system}_neb{neb_num}.png")