from ovito.io import import_file, export_file
from ovito.modifiers import AtomicStrainModifier, SelectTypeModifier, HistogramModifier


def ovito_stress_sum(import_path, particle_type=None):
    pipeline = import_file(import_path)
    if particle_type is not None:
        if particle_type not in range(1, 5):
            raise ValueError("particle_type must be between 1 and 4")
        pipeline.modifiers.append(
            SelectTypeModifier(property="Particle Type", types={particle_type})
        )
    data = pipeline.compute()
    histogram_modifier = HistogramModifier(
        property="v_sa_von",
        bin_count=100,
        only_selected=(particle_type is not None),
    )
    pipeline.modifiers.append(histogram_modifier)
    data = pipeline.compute()

    total_sum = 0
    for bin_entry in data.tables["histogram[v_sa_von]"].xy():
        shear_stress = bin_entry[0]
        count = bin_entry[1]
        total_sum += shear_stress * count

    print(f"Total sum of Shear Stress * Count: {total_sum}")
    return total_sum


ovito_stress_sum(
    "strain_stress/mc300k/after_relax_mc300k.cfg",
)
