import numpy as np
from ovito.io import import_file
from ovito.modifiers import SelectTypeModifier

def ovito_stress_sum(import_path, particle_type=None):
    # Load the particle data
    pipeline = import_file(import_path)

    # Apply particle type selection if specified
    if particle_type is not None:
        if particle_type not in range(1, 5):
            raise ValueError("particle_type must be between 1 and 4")
        pipeline.modifiers.append(
            SelectTypeModifier(property="Particle Type", types={particle_type})
        )
    
    # Compute the pipeline
    data = pipeline.compute()

    # Access the stress data (v_sa_von) and convert to NumPy array
    stress_array = np.array(data.particles['v_sa_von'])

    # If filtering by particle type, sum only for the selected particles
    if particle_type is not None:
        selected = np.array(data.particles['Selection'])  # Binary selection array
        total_sum = stress_array[selected > 0].sum()
    else:
        total_sum = stress_array.sum()

    print(f"Total sum of Shear Stress: {total_sum}")
    return total_sum

# Run the function
ovito_stress_sum(
    "strain_stress/mc300k/after_relax_mc300k.cfg",
)
