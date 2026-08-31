from ovito.io import import_file, export_file
from ovito.modifiers import AtomicStrainModifier, SelectTypeModifier, HistogramModifier
from ovito.pipeline import StaticSource, Pipeline, FileSource
import sys

# Handle command line arguments
if len(sys.argv) != 5:
    print("Usage: python export_strain_diagram.py input_file atom_type ref_file output_file")
    print("Example: python export_strain_diagram.py after_relax.data 1 atomic_strain_ref.data Ni_strain.txt")
    sys.exit(1)

input_file = sys.argv[1]
atom_type = int(sys.argv[2])
ref_file = sys.argv[3]
output_file = sys.argv[4]

def export_strain_diagram(input_file, atom_type, ref_file, output_file):
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

    # Add Select Type modifier to select only specified atom type
    select_mod = SelectTypeModifier()
    select_mod.property = "Particle Type"
    select_mod.types = {atom_type}
    pipeline.modifiers.append(select_mod)

    # Add Histogram modifier with the correct shear strain property name
    histogram_mod = HistogramModifier()
    histogram_mod.property = "Shear Strain"
    histogram_mod.bin_count = 100
    histogram_mod.only_selected = True
    pipeline.modifiers.append(histogram_mod)

    # Compute the pipeline to get results
    data = pipeline.compute()

    # Export the histogram data table using the correct format
    export_file(data.tables['histogram[Shear Strain]'], output_file, "txt/table")

# Call the function directly if script is run as main
if __name__ == "__main__":
    export_strain_diagram(input_file, atom_type, ref_file, output_file)