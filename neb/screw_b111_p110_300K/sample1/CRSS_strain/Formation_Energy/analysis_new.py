# -*- coding: utf-8 -*-
import numpy as np
import ase.io, ase.io.lammpsdata
import math
import csv
from ovito.io import import_file
from ovito.modifiers import DislocationAnalysisModifier, PolyhedralTemplateMatchingModifier
import WarrenCowleyParameters as wc

neighbors = []
csv_rows = []

# 初始化儲存空間 (已新增 hydro)
stats_storage = {
    'von': {},
    'rmsd': {},
    'pea': {},
    'sro': {},
    'saxx': {},
    'sayy': {},
    'hydro': {}
}

base_data_path = "../step_0/neb_1.data"
atoms = ase.io.read(base_data_path, format="lammps-data", style='atomic', Z_of_type={1:28, 2:27, 3:22, 4:40, 5:72})

# --- 第一階段：數據提取 ---
for f_idx in range(6):
    cfg_name = f"md_npt_dump{f_idx+1}.cfg"
    pipe_temp = import_file(cfg_name)

    ptm_temp = PolyhedralTemplateMatchingModifier(rmsd_cutoff=0.3, output_rmsd=True)
    pipe_temp.modifiers.append(ptm_temp)
    
    wc_mod_temp = wc.WarrenCowleyParameters(nneigh=[0, 14], per_particle=True)
    pipe_temp.modifiers.append(wc_mod_temp)
    
    data_temp = pipe_temp.compute()
    
    von_vals = data_temp.particles['v_sa_von']
    saxx_vals = data_temp.particles['v_sa_xx']
    sayy_vals = data_temp.particles['v_sa_yy']
    hydro_vals = data_temp.particles['v_sa_hydro'] # 提取 Hydrostatic Stress
    
    r_key = 'RMSD' if 'RMSD' in data_temp.particles.keys() else 'PTM RMSD'
    rmsd_vals = data_temp.particles[r_key]
    pea_vals = data_temp.particles['v_pea']
    wc_vals = data_temp.particles["Warren-Cowley parameter (shell=1)"]
    atom_types_temp = data_temp.particles['Particle Type']

    for i in range(data_temp.particles.count):
        if i not in stats_storage['von']:
            stats_storage['von'][i] = []
            stats_storage['rmsd'][i] = []
            stats_storage['pea'][i] = []
            stats_storage['sro'][i] = []
            stats_storage['saxx'][i] = []
            stats_storage['sayy'][i] = []
            stats_storage['hydro'][i] = []
        
        stats_storage['von'][i].append(float(von_vals[i]))
        stats_storage['saxx'][i].append(float(saxx_vals[i]))
        stats_storage['sayy'][i].append(float(sayy_vals[i]))
        stats_storage['hydro'][i].append(float(hydro_vals[i]))
        stats_storage['rmsd'][i].append(float(rmsd_vals[i]))
        stats_storage['pea'][i].append(float(pea_vals[i]))
        
        t_i = int(atom_types_temp[i]) - 1
        current_f_sro = []
        for t_j in range(5):
            val = wc_vals[i, t_i * 5 + t_j]
            current_f_sro.append(0.0 if np.isnan(val) else float(val))
        stats_storage['sro'][i].append(current_f_sro)

# --- 第二階段：位錯鄰域搜尋 ---
for f in range(6):
    datafile = "../step_0/neb_"+str(f+1)+".data"
    pipeline = import_file(datafile, atom_style="atomic")
    modifier = DislocationAnalysisModifier()
    modifier.input_crystal_structure = DislocationAnalysisModifier.Lattice.BCC
    modifier.trial_circuit_length = 30
    modifier.circuit_stretchability = 10
    pipeline.modifiers.append(modifier)
    data = pipeline.compute()

    disloc = []
    for segment in data.dislocations.segments:
        for pt in segment.points:
            disloc.append(pt)

    temp_atoms = ase.io.read(datafile, format="lammps-data", style='atomic', Z_of_type={1:28, 2:27, 3:22, 4:40, 5:72})
    pos = temp_atoms.get_positions()
    cell = temp_atoms.get_cell()
    lx, ly, lz = cell[0][0], cell[1][1], cell[2][2]

    for i in range(len(temp_atoms)):
        p_i = pos[i]
        for j in range(len(disloc)):
            d_p = disloc[j]
            dx, dy, dz = p_i[0] - d_p[0], p_i[1] - d_p[1], p_i[2] - d_p[2]
            if dx > lx/2: dx -= lx
            elif dx < -lx/2: dx += lx
            if dy > ly/2: dy -= ly
            elif dy < -ly/2: dy += ly
            if dz > lz/2: dz -= lz
            elif dz < -lz/2: dz += lz
            dist = math.sqrt(dx**2 + dy**2 + dz**2)
            if dist < 10:
                neighbors.append(i)

neighbors_set = set(neighbors)

pipeline_cfg = import_file("md_npt_dump1.cfg")
data_cfg = pipeline_cfg.compute()
atom_ids = data_cfg.particles['Particle Identifier']
atom_types = data_cfg.particles['Particle Type']

config_name = "ConfigureD"

# 更新表頭順序
header = ['Configure','Atom_id','type', 
          'E_atomic_avg', 'E_atomic_max', 'E_atomic_min', 'E_atomic_range',
          'Stress_von_avg', 'Stress_von_max', 'Stress_von_min', 'Stress_von_range',
          'SA_XX_avg', 'SA_XX_max', 'SA_XX_min', 'SA_XX_range',
          'SA_YY_avg', 'SA_YY_max', 'SA_YY_min', 'SA_YY_range',
          'SA_Hydro_avg', 'SA_Hydro_max', 'SA_Hydro_min', 'SA_Hydro_range',
          'PTM_RMSD_avg', 'PTM_RMSD_max', 'PTM_RMSD_min', 'PTM_RMSD_range',
          'WC_Ni', 'WC_Co', 'WC_Ti', 'WC_Zr', 'WC_Hf']

# --- 第三階段：統計計算與輸出 ---
for i in neighbors_set:
    e_list = np.array(stats_storage['pea'][i])
    e_avg, e_max, e_min = np.mean(e_list), np.max(e_list), np.min(e_list)
    e_range = e_max - e_min

    v_list = np.array(stats_storage['von'][i])
    v_avg, v_max, v_min = np.mean(v_list), np.max(v_list), np.min(v_list)
    v_range = v_max - v_min

    saxx_list = np.array(stats_storage['saxx'][i])
    saxx_avg, saxx_max, saxx_min = np.mean(saxx_list), np.max(saxx_list), np.min(saxx_list)
    saxx_range = saxx_max - saxx_min

    sayy_list = np.array(stats_storage['sayy'][i])
    sayy_avg, sayy_max, sayy_min = np.mean(sayy_list), np.max(sayy_list), np.min(sayy_list)
    sayy_range = sayy_max - sayy_min
    
    # 新增 Hydro 統計
    hydro_list = np.array(stats_storage['hydro'][i])
    h_avg, h_max, h_min = np.mean(hydro_list), np.max(hydro_list), np.min(hydro_list)
    h_range = h_max - h_min

    r_list = np.array(stats_storage['rmsd'][i])
    r_avg, r_max, r_min = np.mean(r_list), np.max(r_list), np.min(r_list)
    r_range = r_max - r_min
    
    sro_matrix = np.array(stats_storage['sro'][i]) 
    sro_averages = np.mean(sro_matrix, axis=0).tolist()

    row = [
        config_name,
        int(atom_ids[i]),
        int(atom_types[i]),
        e_avg, e_max, e_min, e_range,
        v_avg, v_max, v_min, v_range,
        saxx_avg, saxx_max, saxx_min, saxx_range,
        sayy_avg, sayy_max, sayy_min, sayy_range,
        h_avg, h_max, h_min, h_range,  # 插入 Hydro 數據
        r_avg, r_max, r_min, r_range
    ] + sro_averages
    
    csv_rows.append(row)
    atoms[i].symbol = 'H'

csv_rows.sort(key=lambda x: x[1])

with open('output_analysis_new.csv', 'w', newline='', encoding='utf-8') as f_csv:
    writer = csv.writer(f_csv)
    writer.writerow(header)
    writer.writerows(csv_rows)

ase.io.lammpsdata.write_lammps_data("test_analysis_new.data", atoms, specorder=['Ni','Co','Ti','Zr','Hf','H'], units='metal', atom_style='atomic')

print(f"Done: {len(csv_rows)} atoms processed with Hydrostatic Stress data.")