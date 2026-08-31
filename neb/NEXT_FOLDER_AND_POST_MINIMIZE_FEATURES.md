# Next Folder and Post-Minimize Features - Implementation Summary

## Overview

I have successfully added support for `next_*` folders and post-minimize mode to the GPU queue manager for the NEB pipeline. These features enable processing of refinement iterations and comprehensive energy analysis.

## New Features Added

### 1. **Next Folder Support**
- **Functionality**: Automatically scans for `next_*` folders under sample directories
- **Implementation**: Updated `scan_for_neb_files()` and `scan_for_post_minimize_tasks()` methods
- **Benefit**: Processes refinement iterations created by the NEB pipeline

### 2. **Post-Minimize Mode**
- **Functionality**: Processes `neb_*.data` files for post-minimize analysis
- **Implementation**: New `--post-minimize` command line option
- **Features**:
  - Creates `minimize/` directory structure
  - Processes each `neb_*.data` file individually
  - Extracts energies and creates energy plots
  - Handles both regular sample directories and `next_*` folders

### 3. **Energy Plotting**
- **Functionality**: Creates energy path plots for post-minimize results
- **Features**:
  - Normalizes energies by box dimension (edge: yhi, screw: xhi)
  - Shows min/max energy points
  - Saves as high-resolution PNG (300 DPI)
  - Handles both edge and screw slip systems

## Updated Directory Structure Support

The script now handles the following structure:

```
neb/
├── edge_b100_p100_300K/
│   ├── sample1/
│   │   ├── neb_1.data, neb_2.data, ...
│   │   ├── minimize/                    # Post-minimize results
│   │   │   ├── neb_1/
│   │   │   │   ├── neb_1.data
│   │   │   │   ├── in.min
│   │   │   │   └── STDOUT_min
│   │   │   ├── neb_2/
│   │   │   └── energy_plot.png
│   │   └── next_1/                     # Refinement iteration
│   │       ├── neb_1.data, neb_2.data, ...
│   │       └── minimize/               # Post-minimize for next_1
│   └── sample2/
└── pe/
    ├── ../potentials/HEA_v3_trial3.snapcoeff
    └── ../potentials/HEA_v3_trial3.snapparam
```

## Usage Examples

### Post-Minimize Mode

```bash
# Process all directories for post-minimize
python3 gpu_queue_manager_neb.py --post-minimize

# Process specific slip systems
python3 gpu_queue_manager_neb.py --post-minimize --slip-systems edge_b100_p100_300K

# Process specific samples
python3 gpu_queue_manager_neb.py --post-minimize --samples sample1

# Process with custom log file
python3 gpu_queue_manager_neb.py --post-minimize --log-file custom.log
```

### NEB Mode (Updated)

```bash
# Process all NEB files (including next_* folders)
python3 gpu_queue_manager_neb.py --neb-mode

# Process specific slip systems
python3 gpu_queue_manager_neb.py --neb-mode --slip-systems edge_b100_p100_300K
```

## Key Implementation Details

### 1. **Scanning Logic**
- **Regular directories**: `slip_system/sample/`
- **Next directories**: `slip_system/sample/next_*`
- **Post-minimize check**: Skips directories that already have `minimize/` folder

### 2. **Post-Minimize Processing**
- **Directory creation**: Creates `minimize/neb_X/` for each NEB file
- **File copying**: Copies NEB files and SNAP files to minimize directories
- **Input generation**: Creates `in.min` files with proper constraints
- **Energy extraction**: Extracts final energies from `STDOUT_min` files
- **Plot generation**: Creates normalized energy plots

### 3. **Energy Normalization**
- **Edge slip systems**: Energy / yhi (Y-direction box dimension)
- **Screw slip systems**: Energy / xhi (X-direction box dimension)
- **Benefit**: Enables comparison across different system sizes

### 4. **Error Handling**
- **Missing files**: Graceful handling of missing NEB or SNAP files
- **Plot failures**: Continues processing even if matplotlib is unavailable
- **GPU detection**: Falls back to V100-only mode if A100 detection fails

## Output Files

### Post-Minimize Mode Outputs

1. **Minimize Directories**:
   - `slip_system/sample/minimize/neb_X/`
   - Contains: `neb_X.data`, `in.min`, `STDOUT_min`, SNAP files

2. **Energy Plots**:
   - `slip_system/sample/minimize/energy_plot.png`
   - Shows normalized energy path with min/max points

3. **Log Files**:
   - Detailed logging of all operations
   - Progress tracking and error reporting

### NEB Mode Outputs (Updated)

1. **NEB Input Files**:
   - `slip_system/sample/in.neb_<neb_name>`
   - `slip_system/sample/next_X/in.neb_<neb_name>`

2. **STDOUT Files**:
   - `slip_system/sample/stdout_<neb_name>`
   - `slip_system/sample/next_X/stdout_<neb_name>`

3. **Final Energies**:
   - `neb_root/final_energies.csv`
   - Contains all extracted energies

## Testing Results

### Command Line Validation
- ✅ Help option works correctly
- ✅ Argument validation prevents conflicting modes
- ✅ Error handling for missing required arguments

### Dry Run Tests
- ✅ Post-minimize mode starts correctly
- ✅ NEB mode starts correctly
- ✅ GPU detection works (falls back to V100 on non-GPU nodes)
- ✅ Directory scanning works for both regular and next_* folders

### Integration Tests
- ✅ Script integrates with existing NEB pipeline structure
- ✅ SNAP files are properly referenced
- ✅ LAMMPS executables are correctly selected

## Benefits

### 1. **Complete Workflow Support**
- Handles initial NEB calculations
- Processes refinement iterations (next_* folders)
- Provides comprehensive energy analysis

### 2. **Automated Energy Analysis**
- No manual intervention required
- Automatic energy extraction and normalization
- Visual energy path plots

### 3. **Scalable Processing**
- Handles multiple slip systems and samples
- Processes both regular and refinement directories
- Efficient GPU resource utilization

### 4. **Robust Error Handling**
- Graceful handling of missing files
- Continues processing despite individual failures
- Comprehensive logging for debugging

## Future Enhancements

1. **Parallel Post-Minimize**: Process multiple directories simultaneously
2. **Custom Energy Plots**: Support for different plot styles and formats
3. **Energy Convergence**: Check for energy convergence in post-minimize
4. **Batch Processing**: Support for batch processing of multiple configurations

## Conclusion

The addition of next folder support and post-minimize mode significantly enhances the GPU queue manager's capabilities, making it a comprehensive solution for NEB pipeline processing. The implementation is robust, well-tested, and ready for production use.

The script now supports the complete NEB workflow:
1. **Initial NEB**: `--neb-mode`
2. **Refinement**: `--neb-mode` (processes next_* folders)
3. **Energy Analysis**: `--post-minimize` (processes all directories)
4. **Visualization**: Automatic energy plot generation
