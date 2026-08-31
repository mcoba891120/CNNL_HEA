from ovito.io import import_file, export_file
from ovito.modifiers import AtomicStrainModifier, SelectTypeModifier, HistogramModifier


def ovito_strain_sum(import_path, reference_path, particle_type=None):
    pipeline = import_file(import_path)
    reference_pipeline = import_file(reference_path)
    atomic_strain_modifier = AtomicStrainModifier(cutoff=3.5)
    pipeline.modifiers.append(atomic_strain_modifier)
    atomic_strain_modifier.reference = reference_pipeline.source
    if particle_type is not None:
        if particle_type not in range(1, 5):
            raise ValueError("particle_type must be between 1 and 4")
        pipeline.modifiers.append(
            SelectTypeModifier(property="Particle Type", types={particle_type})
        )
    data = pipeline.compute()
    histogram_modifier = HistogramModifier(
        property="Shear Strain",
        bin_count=100,
        only_selected=(particle_type is not None),
    )
    pipeline.modifiers.append(histogram_modifier)
    data = pipeline.compute()

    total_sum = 0
    for bin_entry in data.tables["histogram[Shear Strain]"].xy():
        shear_strain = bin_entry[0]
        count = bin_entry[1]
        total_sum += shear_strain * count

    print(f"Total sum of Shear Strain * Count: {total_sum}")
    return total_sum


ovito_strain_sum(
    "dislocation/stress_strain_extraction/edge_b100_p100/after_relax.data",
    "dislocation/stress_strain_extraction/edge_b100_p100/atomic_strain_ref.data",
)
