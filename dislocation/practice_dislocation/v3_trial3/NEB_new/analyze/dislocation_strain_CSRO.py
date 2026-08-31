import os
import sys
import numpy as np
import csv
from ase.io.lammpsdata import read_lammps_data
from ovito.io import import_file
from ovito.modifiers import DislocationAnalysisModifier, AtomicStrainModifier
from ovito.pipeline import FileSource

def get_dislocation_points(input_file):
    pipeline = import_file(input_file)
    mod = DislocationAnalysisModifier()
    mod.input_crystal_structure = DislocationAnalysisModifier.Lattice.BCC
    mod.defect_mesh_smoothing_level = 10
    mod.trial_circuit_length = 80
    mod.circuit_stretchability = 10
    mod.line_point_separation = 0.5
    pipeline.modifiers.append(mod)
    data = pipeline.compute()
    pts = []
    for seg in data.dislocations.segments:
        for p in seg.points:
            pts.append((p[0], p[1], p[2]))
    return np.array(pts)


def compute_strains(input_file, ref_file):
    pipeline = import_file(input_file)
    mod = AtomicStrainModifier()
    mod.cutoff = 3.5
    mod.minimum_image_convention = True
    mod.select_invalid_particles = True
    mod.reference = FileSource(); mod.reference.load(ref_file)
    pipeline.modifiers.append(mod)
    data = pipeline.compute()
    return data.particles['Shear Strain'][...]


def get_atoms_near_points(points, positions, cell, rcut):
    pts = np.array(points)
    L = np.array(cell)
    ids = set()
    for p in pts:
        disp = positions - p
        disp -= np.round(disp / L) * L
        d = np.linalg.norm(disp, axis=1)
        ids.update(np.where(d <= rcut)[0].tolist())
    return list(ids)


def rcut_strain_composition(input_file, ref_file, prefix):
    points = get_dislocation_points(input_file)
    ztype = {1:28,2:27,3:22,4:40,5:72}
    atoms = read_lammps_data(input_file, atom_style='atomic', Z_of_type=ztype)
    positions = atoms.get_positions()
    numbers = atoms.get_atomic_numbers()
    cell = np.array(atoms.cell.cellpar()[:3])
    strains = compute_strains(input_file, ref_file)

    results = []
    for rcut in np.linspace(3.0, 10.0, 71):
        atom_ids = get_atoms_near_points(points, positions, cell, rcut)
        strain_sum = {28:0.0,27:0.0,22:0.0,40:0.0,72:0.0}
        for i in atom_ids:
            z = numbers[i]
            if z in strain_sum and not np.isnan(strains[i]):
                strain_sum[z] += strains[i]
        total = sum(strain_sum.values())
        ratios = {z:(strain_sum[z]/total if total>0 else 0.0) for z in strain_sum}
        entry = {'rcut': round(rcut,3), 'count': len(atom_ids)}
        for z in sorted(ratios):
            entry[f'strain_ratio_{z}'] = round(ratios[z],4)
        results.append(entry)

    csv_file = f"{prefix}_strain_composition.csv"
    fields = ['rcut','count'] + [f'strain_ratio_{z}' for z in sorted(ratios)]
    with open(csv_file,'w',newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved strain composition scan to {csv_file}")

    # Plotting
    import matplotlib.pyplot as plt
    rcuts = [r['rcut'] for r in results]
    ratios = {z: [r[f'strain_ratio_{z}'] for r in results] for z in [28,27,22,40,72]}
    labels = {28:'Ni',27:'Co',22:'Ti',40:'Zr',72:'Hf'}

    plt.figure(figsize=(10,8))
    plt.suptitle(f"{prefix} Strain Composition vs RCUT")

    # Ni & Co subplot
    ax1 = plt.subplot(2,1,1)
    ax1.plot(rcuts, ratios[28], label=labels[28])
    ax1.plot(rcuts, ratios[27], label=labels[27])
    ax1.set_ylabel('Strain Ratio')
    ax1.set_title('Ni & Co Strain Contribution')
    ax1.legend()
    ax1.grid(True)

    # Ti, Zr & Hf subplot
    ax2 = plt.subplot(2,1,2)
    ax2.plot(rcuts, ratios[22], label=labels[22])
    ax2.plot(rcuts, ratios[40], label=labels[40])
    ax2.plot(rcuts, ratios[72], label=labels[72])
    ax2.set_xlabel('rcut (Å)')
    ax2.set_ylabel('Strain Ratio')
    ax2.set_title('Ti, Zr & Hf Strain Contribution')
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout(rect=[0,0.03,1,0.95])
    plot_file = f"{prefix}_strain_composition.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved strain composition plot to {plot_file}")


def replace_high_strain_atoms_with_au(input_file, ref_file, output_file, num_atoms=100):
    """
    Find the top N atoms with highest strain and replace them with Au atoms.
    
    Args:
        input_file: Input LAMMPS data file
        ref_file: Reference file for strain calculation
        output_file: Output file name
        num_atoms: Number of atoms to replace (default: 100)
    """
    # Read atoms and compute strains
    ztype = {1:28, 2:27, 3:22, 4:40, 5:72}
    atoms = read_lammps_data(input_file, atom_style='atomic', Z_of_type=ztype)
    strains = compute_strains(input_file, ref_file)
    
    # Find atoms with valid strain values
    valid_indices = ~np.isnan(strains)
    valid_strains = strains[valid_indices]
    valid_atom_indices = np.where(valid_indices)[0]
    
    # Sort by strain (descending) and get top N atoms
    sorted_indices = np.argsort(valid_strains)[::-1]
    top_n_indices = valid_atom_indices[sorted_indices[:num_atoms]]
    
    # Replace these atoms with Au (atomic number 79)
    numbers = atoms.get_atomic_numbers()
    numbers[top_n_indices] = 79
    
    # Update atom types for LAMMPS data format
    # Find the maximum existing type and add Au as a new type
    existing_types = set()
    for atom in atoms:
        if atom.number in ztype.values():
            # Find the type number for this atomic number
            for type_num, atomic_num in ztype.items():
                if atomic_num == atom.number:
                    existing_types.add(type_num)
                    break
    
    max_type = max(existing_types) if existing_types else 0
    au_type = max_type + 1
    
    # Update the ztype dictionary to include Au
    ztype[au_type] = 79
    
    # Update atom types in the atoms object
    # We need to create a mapping from atomic numbers to type numbers
    atomic_to_type = {atomic_num: type_num for type_num, atomic_num in ztype.items()}
    
    # Create new atoms object with updated types
    from ase import Atoms
    new_atoms = Atoms(
        numbers=numbers,
        positions=atoms.get_positions(),
        cell=atoms.get_cell(),
        pbc=atoms.get_pbc()
    )
    
    # Write the modified structure
    from ase.io.lammpsdata import write_lammps_data
    write_lammps_data(output_file, new_atoms, atom_style='atomic', Z_of_type=ztype)
    
    # Print summary
    print(f"Replaced {len(top_n_indices)} atoms with highest strain with Au atoms")
    print(f"Top 10 strain values: {valid_strains[sorted_indices[:10]]}")
    print(f"Saved modified structure to {output_file}")
    
    # Save strain information for replaced atoms
    strain_info_file = output_file.replace('.data', '_strain_info.csv')
    with open(strain_info_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Atom_Index', 'Original_Atomic_Number', 'Strain_Value'])
        for i, atom_idx in enumerate(top_n_indices):
            original_z = atoms.get_atomic_numbers()[atom_idx]
            strain_val = strains[atom_idx]
            writer.writerow([atom_idx, original_z, strain_val])
    
    print(f"Saved strain information for replaced atoms to {strain_info_file}")


def main():
    if len(sys.argv) < 4:
        print(f"Usage: python {sys.argv[0]} <input.data> <ref.data> <prefix> [--replace-au] [num_atoms]")
        print("  --replace-au: Replace top N atoms with highest strain with Au atoms")
        print("  num_atoms: Number of atoms to replace (default: 100)")
        sys.exit(1)
    
    infile, reffile, prefix = sys.argv[1:4]
    
    # Check if --replace-au flag is present
    if len(sys.argv) > 4 and sys.argv[4] == '--replace-au':
        num_atoms = 100  # default
        if len(sys.argv) > 5:
            try:
                num_atoms = int(sys.argv[5])
            except ValueError:
                print("Error: num_atoms must be an integer")
                sys.exit(1)
        
        output_file = f"{prefix}_with_au.data"
        replace_high_strain_atoms_with_au(infile, reffile, output_file, num_atoms)
    else:
        rcut_strain_composition(infile, reffile, prefix)

if __name__=='__main__':
    main()
