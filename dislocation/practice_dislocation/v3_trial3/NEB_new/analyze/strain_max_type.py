from ovito.io import import_file, export_file
from ovito.modifiers import AtomicStrainModifier, SelectTypeModifier, HistogramModifier, AssignColorModifier
from ovito.pipeline import StaticSource, Pipeline, FileSource
import numpy as np
import sys

# Handle command line arguments
if len(sys.argv) != 5:
    print("Usage: python export_strain_diagram.py input_file atom_type ref_file output_file")
    print("Example: python export_strain_diagram.py after_relax.data 1 atomic_strain_ref.data Ni_strain.data")
    sys.exit(1)

input_file = sys.argv[1]
atom_type = int(sys.argv[2])
ref_file = sys.argv[3]
output_file = sys.argv[4]

def export_strain_diagram_with_ag_markers(input_file, atom_type, ref_file, output_file):
    # Import the main simulation file
    pipeline = import_file(input_file)

    # Add Atomic Strain modifier with your specified settings
    strain_mod = AtomicStrainModifier()
    strain_mod.cutoff = 3.5
    strain_mod.minimum_image_convention = True
    strain_mod.select_invalid_particles = True

    # Set reference to external file
    strain_mod.reference = FileSource()
    strain_mod.reference.load(ref_file)

    # Add the strain modifier to the pipeline
    pipeline.modifiers.append(strain_mod)

    # First compute to get strain values
    data = pipeline.compute()

    # Get particle properties
    particle_types = data.particles['Particle Type'][...]
    shear_strains = data.particles['Shear Strain'][...]
    
    # Find indices of specified atom type
    type_mask = (particle_types == atom_type)
    type_indices = np.where(type_mask)[0]
    
    if len(type_indices) == 0:
        print(f"Warning: No atoms of type {atom_type} found!")
        return
    
    # Get shear strain values for the specified type
    type_shear_strains = shear_strains[type_indices]
    
    # Find indices of top 10 highest strain atoms of the specified type
    # Sort by shear strain in descending order
    sorted_indices = np.argsort(type_shear_strains)[::-1]
    top10_relative_indices = sorted_indices[:10]
    top10_absolute_indices = type_indices[top10_relative_indices]
    
    print(f"Found {len(type_indices)} atoms of type {atom_type}")
    print(f"Top 10 highest shear strain values for type {atom_type}:")
    for i, idx in enumerate(top10_absolute_indices):
        print(f"  {i+1}. Atom {idx}: Shear Strain = {shear_strains[idx]:.6f}")
    
    # Create a new particle type array
    new_particle_types = particle_types.copy()
    
    # Assume Ag has particle type 47 (atomic number of silver)
    # You can change this value if needed
    ag_type = 47
    
    # Change the top 10 highest strain atoms to Ag
    new_particle_types[top10_absolute_indices] = ag_type
    
    # Create a new data collection with modified particle types
    from ovito.data import DataCollection, ParticleProperty
    
    # Create a modifier to change particle types
    def modify_particle_types(frame, data):
        # Replace the particle type property
        data.particles_.create_property('Particle Type', data=new_particle_types)
    
    # Apply the modification
    pipeline.modifiers.append(modify_particle_types)
    
    # Add color coding for visualization (optional)
    color_mod = AssignColorModifier()
    color_mod.color_by_property = 'Particle Type'
    pipeline.modifiers.append(color_mod)
    
    # Compute the final result
    final_data = pipeline.compute()
    
    # Export the modified structure
    export_file(final_data, output_file, "lammps/data", 
                columns=["Particle Identifier", "Particle Type", "Position.X", "Position.Y", "Position.Z"])
    
    print(f"\nModified structure exported to: {output_file}")
    print(f"Changed {len(top10_absolute_indices)} atoms from type {atom_type} to type {ag_type} (Ag)")
    print("These are the atoms with the highest shear strain values.")
    
    # Also create a summary file with strain information
    summary_file = output_file.replace('.data', '_strain_summary.txt')
    with open(summary_file, 'w') as f:
        f.write("Top 10 Highest Shear Strain Atoms (Changed to Ag)\n")
        f.write("=" * 50 + "\n")
        f.write("Atom_ID\tOriginal_Type\tNew_Type\tShear_Strain\n")
        for i, idx in enumerate(top10_absolute_indices):
            f.write(f"{idx}\t{atom_type}\t{ag_type}\t{shear_strains[idx]:.6f}\n")
    
    print(f"Strain summary saved to: {summary_file}")

# Call the function directly if script is run as main
if __name__ == "__main__":
    export_strain_diagram_with_ag_markers(input_file, atom_type, ref_file, output_file)