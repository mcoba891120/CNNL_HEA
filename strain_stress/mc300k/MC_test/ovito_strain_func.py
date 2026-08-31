import numpy as np
from ovito.io import import_file
from ovito.modifiers import AtomicStrainModifier, SelectTypeModifier

def ovito_strain_sum(import_path, reference_path, particle_type=None):
    # Import the atomic configuration and reference configuration
    pipeline = import_file(import_path)
    reference_pipeline = import_file(reference_path)
    
    # Add atomic strain modifier
    atomic_strain_modifier = AtomicStrainModifier(cutoff=3.5)
    pipeline.modifiers.append(atomic_strain_modifier)
    atomic_strain_modifier.reference = reference_pipeline.source
    
    # Optionally select particles of a certain type
    if particle_type is not None:
        if particle_type not in range(1, 5):
            raise ValueError("particle_type must be between 1 and 4")
        pipeline.modifiers.append(
            SelectTypeModifier(property="Particle Type", types={particle_type})
        )
    
    # Compute the modified data
    data = pipeline.compute()
    
    # Access the shear strain data and convert it to a NumPy array
    shear_strain_array = np.array(data.particles['Shear Strain'])

    # If filtering by particle type, only sum for selected particles
    if particle_type is not None:
        selected = np.array(data.particles['Selection'])  # Binary selection array
        total_sum = shear_strain_array[selected > 0].sum()
    else:
        total_sum = shear_strain_array.sum()

    print(f"Total sum of Shear Strain: {total_sum}")
    return total_sum


ovito_strain_sum(import_path="strain_stress/mc300k/after_relax.data",reference_path="strain_stress/mc300k/atomic_strain_ref.data")