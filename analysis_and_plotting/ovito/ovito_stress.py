from ovito.io import import_file, export_file
from ovito.modifiers import AtomicStrainModifier, SelectTypeModifier, HistogramModifier

pipeline = import_file(
    "strain_stress/mc300k/after_relax_mc300k.cfg"
)

pipeline.modifiers.append(SelectTypeModifier(property="Particle Type", types={1}))

data = pipeline.compute()

print("Available properties:", data.particles.keys())

histogram_modifier = HistogramModifier(
    property="v_sa_von", bin_count=100, only_selected=True
)
pipeline.modifiers.append(histogram_modifier)

data = pipeline.compute()

print("Available table identifiers:", list(data.tables.keys()))

with open("output_stress_histogram.txt", "w") as file:
    file.write("# Shear Strain (100 data points):\n")
    file.write('# "Shear Stress" Count\n')
    for bin_entry in data.tables["histogram[v_sa_von]"].xy():
        file.write(f"{bin_entry[0]} {bin_entry[1]} \n")

print("Histogram data has been written to output_stress_histogram.txt")
