from ovito.io import import_file, export_file
from ovito.modifiers import AtomicStrainModifier, SelectTypeModifier, HistogramModifier
def ovito_strain_sum(import_file,reference_file):
    pipeline = import_file
    reference_pipeline = reference_file
    atomic_strain_modifier = AtomicStrainModifier(cutoff=3.5)
    pipeline.modifiers.append(atomic_strain_modifier)
    atomic_strain_modifier.reference = reference_pipeline.source
    pipeline.modifiers.append(SelectTypeModifier(property="Particle Type", types={1}))
    data = pipeline.compute()
    histogram_modifier = HistogramModifier(property="Shear Strain", bin_count=100, only_selected=True)
    pipeline.modifiers.append(histogram_modifier)
    data = pipeline.compute()
    with open("output_strain_histogram.txt", "w") as file:
        file.write("# Shear Strain (100 data points):\n")
        file.write('# "Shear Strain" Count\n')
        for bin_entry in data.tables["histogram[Shear Strain]"].xy():
            file.write(f"{bin_entry[0]} {bin_entry[1]} \n")
    print("Histogram data has been written to output_strain_histogram.txt")
    return
pipeline = import_file(
    "dislocation/stress_strain_extraction/edge_b100_p100/after_relax.data"
)

reference_pipeline = import_file(
    "dislocation/stress_strain_extraction/edge_b100_p100/atomic_strain_ref.data"
)

atomic_strain_modifier = AtomicStrainModifier(cutoff=3.5)
pipeline.modifiers.append(atomic_strain_modifier)

atomic_strain_modifier.reference = reference_pipeline.source

pipeline.modifiers.append(SelectTypeModifier(property="Particle Type", types={1}))

data = pipeline.compute()

print("Available properties:", data.particles.keys())

histogram_modifier = HistogramModifier(
    property="Shear Strain", bin_count=100, only_selected=True
)
pipeline.modifiers.append(histogram_modifier)

data = pipeline.compute()

print("Available table identifiers:", list(data.tables.keys()))

with open("output_strain_histogram.txt", "w") as file:
    file.write("# Shear Strain (100 data points):\n")
    file.write('# "Shear Strain" Count\n')
    for bin_entry in data.tables["histogram[Shear Strain]"].xy():
        file.write(f"{bin_entry[0]} {bin_entry[1]} \n")

print("Histogram data has been written to output_strain_histogram.txt")
