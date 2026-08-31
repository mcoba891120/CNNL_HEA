#!/bin/bash

VERSION=$1
RELAX_FILE_BASE_PATH="relaxation/NiCoTiZrHf_110/5quinary"
VERSION_DIR="$RELAX_FILE_BASE_PATH/$VERSION"
CUR_DIR=$(pwd)
OUTPUT_VERSION_DIR="$CUR_DIR/$VERSION"
ELEMENTS=("Ni" "Co" "Ti" "Zr" "Hf")

# Check if version parameter is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 version_name"
    echo "Example: $0 v3_trial3"
    exit 1
fi

# Check if the version directory exists
if [ ! -d "$VERSION_DIR" ]; then
    echo "Version directory $VERSION_DIR does not exist."
    exit 1
fi

# Check if required files exist in current directory
if [ ! -f "$CUR_DIR/export_strain_diagram.py" ]; then
    echo "Error: export_strain_diagram.py does not exist in current directory."
    exit 1
fi

if [ ! -f "$CUR_DIR/reshape.sh" ]; then
    echo "Error: reshape.sh does not exist in current directory."
    exit 1
fi

if [ ! -f "$CUR_DIR/in.reshape" ]; then
    echo "Error: in.reshape does not exist in current directory."
    exit 1
fi

# Check if atomsk is available
command -v atomsk >/dev/null 2>&1 || { echo "Error: atomsk is required but not installed or not in PATH"; exit 1; }

# Create output version directory
mkdir -p "$OUTPUT_VERSION_DIR"
echo "Created output directory: $OUTPUT_VERSION_DIR"

# Copy necessary files to the output version directory
cp "$CUR_DIR/reshape.sh" "$OUTPUT_VERSION_DIR/"
cp "$CUR_DIR/in.reshape" "$OUTPUT_VERSION_DIR/"
cp "$CUR_DIR/export_strain_diagram.py" "$OUTPUT_VERSION_DIR/"
chmod +x "$OUTPUT_VERSION_DIR/reshape.sh"

# Get all subdirectories under the version directory and make the same directory structure under the output version directory
for dir in "$VERSION_DIR"/*/; do
    dir_name=$(basename "$dir")
    mkdir -p "$OUTPUT_VERSION_DIR/$dir_name"
    
    echo "Processing $dir_name..."
    
    # Determine the correct input file based on folder name
    if [[ "$dir_name" == *"b100p110"* ]]; then
        input_template="$RELAX_FILE_BASE_PATH/NiCoTiZrHf_b100p110.data"
    elif [[ "$dir_name" == *"b111p110"* ]]; then
        input_template="$RELAX_FILE_BASE_PATH/NiCoTiZrHf_b111p110.data"
    else
        echo "Could not determine template type for folder: $dir_name"
        continue
    fi
    
    # Define file paths
    relax_file="$dir/after_relax.data"
    template_copy="$OUTPUT_VERSION_DIR/$dir_name/template.data"
    enlarged_template="$OUTPUT_VERSION_DIR/$dir_name/after_relax_input.data"
    ref_file="$OUTPUT_VERSION_DIR/$dir_name/atomic_strain_ref.data"
    
    # Copy the template file to the output directory
    cp "$input_template" "$template_copy"
    
    # Use atomsk to duplicate the template along x-direction (2x)
    cd "$OUTPUT_VERSION_DIR/$dir_name"
    echo "Duplicating template file along x-axis..."
    
    
    if [ ! -f "$enlarged_template" ]; then
        atomsk "$template_copy" -duplicate 2 1 1 lmp temp.lmp && mv temp.lmp "$enlarged_template"
        if [ $? -ne 0 ]; then
            echo "Error: Failed to duplicate template file for $dir_name"
            continue
        fi
        continue
    fi
    
    # Change to output version directory to run reshape.sh
    cd "$OUTPUT_VERSION_DIR"
    
    # Run reshape.sh with the enlarged template
    echo "Running reshape for $dir_name using enlarged template..."
    ./reshape.sh "$enlarged_template" "$relax_file" "$ref_file"
    
    # Process each atom type

    for i in {1..5}; do
        element="${ELEMENTS[$((i-1))]}"
        output_file="$OUTPUT_VERSION_DIR/$dir_name/${element}_strain.txt"
        
        echo "Generating strain diagram for $element..."
        python export_strain_diagram.py "$relax_file" "$i" "$ref_file" "$output_file"
        
        echo "Exported $element strain diagram to $output_file"
    done
    
    echo "Completed processing for $dir_name"
    echo "----------------------------------------"
done

echo "All processing complete for version $VERSION"