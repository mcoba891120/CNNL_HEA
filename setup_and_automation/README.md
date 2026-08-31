# Simulation Setup Script

This bash script automates the setup process for running molecular dynamics simulations using LAMMPS. It's designed to work with different simulation modes, alloys, and orientations.

## Which script to use

Several near-identically-named scripts live in this folder; they are not
redundant copies of each other:

- **`auto_simulation.sh`** — the main, most complete driver (all
  simulation modes including `tension`, interactive GPU selection,
  multi-host dispatch). Use this by default.
- **`04_MC_auto_simulation.sh`** — same idea, but its default
  `STRUCTURE_PATH` continues from a Monte Carlo run's output
  (`$USER_DIR/MC/$TEMPERATURE/mc_folder/emin_2.lmp`) instead of a plain
  relax run's `after_relax.data`. Use this specifically for
  compress-after-MC pipelines.
- **`HEA_gen.py`** — structure generator for the 4-element NiCoTiZr
  system (Ni → half Co, half Zr).
- **`NiCoTiZrHf_HEA_gen.py`** — a *different* generator, for the
  5-element NiCoTiZrHf system (Ni → Co, Ti → split between Zr and Hf).
  Not a duplicate of `HEA_gen.py` — different alloy, different logic.

Two other near-duplicate drivers (`NiCoTiZrHf_auto_simulation.sh`,
`NiCoTiZrHf_HEA.sh`) and one fully-hardcoded early prototype (`HEA.py`,
no CLI args at all) were removed during cleanup — they added no
capability `auto_simulation.sh`/`HEA_gen.py` didn't already cover and
weren't referenced by any other script in this repo.

## Features

- Interactive setup for simulation parameters
- Supports multiple simulation modes: relax, heat, compress
- Customizable alloy composition and crystal orientation
- Automatic directory structure creation
- Generation of structure files using Atomsk and a custom Python script
- Dynamic creation of LAMMPS input files based on templates
- Automatic job submission on supported systems

## Prerequisites

- Bash shell
- LAMMPS
- Atomsk
- Python (for running HEA_gen.py)
- MPI

## Usage

1. Place the script, input template file, HEA_gen.py, and pe directory in the directory where you want to set up your simulations.
2. Make the script executable:
   ```
   chmod +x script_name.sh
   ```
3. Run the script:
   ```
   ./script_name.sh
   ```
4. Follow the prompts to set up your simulation.

## Input Parameters

The script will prompt you for the following information:

- Simulation mode (relax, heat, compress)
- Alloy composition (default: NiCoTiZr)
- Crystal orientation (100, 100, 111)
- Session name
- Lattice duplication factors (X, Y, Z)
- Potential energy (PE) number
- Number of CPU cores to use
- Number of simulation runs
- Temperature (for compress mode only)

## Directory Structure

The script creates the following directory structure:

```
└── [Simulation Mode]
    └── [Alloy]_[Orientation]
        ├── structure
        │   ├── [Alloy]_[TotalAtoms].pos
        │   └── [Alloy]_[TotalAtoms].lmp
        └── [Session Name]
            └── in.[SimulationMode].[Alloy].[SessionName]
```

## Supported Systems

The script supports automatic job submission on the following systems:
- amd01
- sophon (provides instructions for manual submission)

## Notes

- Make sure to have the necessary input files (in.relax.var.[Alloy], in.compress.var.[Alloy], etc.) in the same directory as the script.
- The HEA_gen.py script should be available in the user's directory.
- pe directory that contains different coeff and param should be available inteh user's directory
- Modify the LAMMPS executable path if necessary.

## Troubleshooting

If you encounter any issues:
- Check that all required software (LAMMPS, Atomsk, Python) is installed and in your PATH.
- Ensure you have the necessary permissions to create directories and files.
- Verify that all required input files are present in the correct locations.

For further assistance, please contact the script maintainer.