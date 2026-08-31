from ovito.io import import_file, export_file
from ovito.modifiers import AtomicStrainModifier
from ovito.pipeline import FileSource
import numpy as np
import sys
import os

atoms_num = 1000
# Thickness (in same units as positions) for boundary exclusion
boundary_thickness = 5.0
# Ag particle type (atomic number)
ag_type = 47

def export_strain_diagram_with_ag_markers(input_file, ref_file, output_file):
    # 1. Import data and set up strain modifier
    pipeline = import_file(input_file)
    strain_mod = AtomicStrainModifier()
    strain_mod.cutoff = 3.5
    strain_mod.minimum_image_convention = True
    strain_mod.select_invalid_particles = True
    strain_mod.reference = FileSource();  strain_mod.reference.load(ref_file)
    pipeline.modifiers.append(strain_mod)

    # 2. Compute initial data
    data      = pipeline.compute()
    positions = data.particles['Position'][...]
    types     = data.particles['Particle Type'][...]
    strains   = data.particles['Shear Strain'][...]

    # 3. Determine z-range and central region (exclude boundaries)
    z_vals    = positions[:, 2]
    z_min, z_max = z_vals.min(), z_vals.max()
    central_mask = (z_vals > z_min + boundary_thickness) & (z_vals < z_max - boundary_thickness)

    # 4. Mask out invalid strains and boundary atoms
    valid_mask = ~np.isnan(strains) & ~np.isinf(strains) & central_mask
    valid_indices = np.where(valid_mask)[0]
    if len(valid_indices) == 0:
        print("Warning: No valid central atoms found!")
        return

    # 5. Select top-10 highest-strain atoms
    sorted_rel = np.argsort(strains[valid_indices])[::-1]
    top10_rel  = sorted_rel[:atoms_num]
    top10_abs  = valid_indices[top10_rel]

    print(f"Found {len(valid_indices)} valid central atoms")
    print("Top 10 highest shear strain atoms (central region):")
    for rank, idx in enumerate(top10_abs, start=1):
        zc = positions[idx, 2]
        print(f"  {rank}. Atom {idx} (Type {types[idx]}, Z={zc:.3f}): Strain={strains[idx]:.6f}")

    # 6. Create new type array and mark top-10 as Ag
    new_types = types.copy()
    new_types[top10_abs] = ag_type

    # 7. Modifier to override particle types
    def assign_ag(frame, data):
        data.particles_.create_property('Particle Type', data=new_types)
    pipeline.modifiers.append(assign_ag)

    # 8. Compute and export
    final = pipeline.compute()
    export_file(final, output_file, "lammps/data")
    print(f"Exported modified data to: {output_file}")

def process_case(input_file, ref_file, prefix):
    """
    處理單一案例的應變最大值分析
    
    Args:
        input_file: 輸入的LAMMPS data檔案
        ref_file: 參考的LAMMPS data檔案
        prefix: 檔案前綴
    """
    # 創建輸出目錄結構
    output_dir = f"strain_max/{atoms_num}"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"{prefix}_strain_max_{atoms_num}.data")
    print(f"開始處理: {prefix}")
    print(f"輸入檔案: {input_file}")
    print(f"參考檔案: {ref_file}")
    print(f"輸出檔案: {output_file}")
    
    try:
        export_strain_diagram_with_ag_markers(input_file, ref_file, output_file)
        print(f"完成處理: {prefix}")
    except Exception as e:
        print(f"處理 {prefix} 時發生錯誤: {e}")

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

    # 檢查命令行參數來決定執行方式
    if len(sys.argv) == 1:
        # 預設執行所有案例
        print("執行所有案例的應變最大值分析...")
        for subdir_in, subdir_ref, prefix in cases:
            input_path = os.path.join(base, subdir_in)
            ref_path = os.path.join(base, subdir_ref)
            process_case(input_path, ref_path, prefix)
    elif len(sys.argv) >= 4:
        # 執行單一案例
        infile, ref, prefix = sys.argv[1:4]
        process_case(infile, ref, prefix)
    else:
        print("使用方法:")
        print("  python strain_max.py                                    # 執行所有案例")
        print("  python strain_max.py input.data ref.data prefix        # 執行單一案例")

if __name__ == '__main__':
    main()
