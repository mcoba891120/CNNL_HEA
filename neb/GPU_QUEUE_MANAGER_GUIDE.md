# GPU Queue Manager for NEB Pipeline - Usage Guide

> **Note:** `gpu_queue_manager_neb.py` itself is not present in this repo
> (only `test_gpu_queue_manager.py`, which calls it, and this guide, which
> documents it, are). This isn't a reorganization artifact — it wasn't
> found in the original source tree pulled for this repo either, so
> either it was never written, or it lived somewhere this pull never
> reached. Everything below describes the intended interface, not
> something you can currently run from this repo as-is.

## Overview

The `gpu_queue_manager_neb.py` script is an adapted version of the original GPU queue manager, specifically designed to work with the NEB pipeline folder structure. It manages GPU resources for processing NEB minimization tasks across multiple slip systems and samples.

## Key Features

- **GPU Detection**: Automatically detects A100 and V100 GPUs
- **Resource Management**: Manages job queues with appropriate limits
- **NEB Mode**: Processes `neb_*.data` files for minimization
- **Post-Minimize Mode**: Processes `neb_*.data` files for post-minimize analysis
- **Next Folder Support**: Handles `next_*` folders under sample directories
- **Multi-Sample Support**: Handles multiple slip systems and samples
- **Energy Extraction**: Automatically extracts final energies from completed tasks
- **Energy Plotting**: Creates energy path plots for post-minimize results
- **Logging**: Comprehensive logging for monitoring and debugging

## Directory Structure

The script works with the following NEB pipeline structure:

```
neb/
├── edge_b100_p100_300K/
│   ├── sample1/
│   │   ├── neb_1.data
│   │   ├── neb_2.data
│   │   ├── next_1/
│   │   │   ├── neb_1.data
│   │   │   ├── neb_2.data
│   │   │   └── ...
│   │   └── ...
│   └── sample2/
├── edge_b100_p110_300K/
│   └── sample1/
├── screw_b100_p100_300K/
│   └── sample1/
└── pe/
    ├── ../potentials/HEA_v3_trial3.snapcoeff
    └── ../potentials/HEA_v3_trial3.snapparam
```

## Installation and Setup

1. **Make the script executable**:
   ```bash
   chmod +x gpu_queue_manager_neb.py
   ```

2. **Verify SNAP files exist**:
   ```bash
   ls -la pe/HEA_v3_trial3.snap*
   ```

3. **Check LAMMPS executables**:
   ```bash
   ls -la /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_*
   ```

## Usage Examples

### Basic Usage

```bash
# NEB Mode: Process all NEB files for minimization
python3 gpu_queue_manager_neb.py --neb-mode

# Post-Minimize Mode: Process all NEB files for post-minimize analysis
python3 gpu_queue_manager_neb.py --post-minimize

# Process specific slip systems
python3 gpu_queue_manager_neb.py --neb-mode --slip-systems edge_b100_p100_300K edge_b100_p110_300K
python3 gpu_queue_manager_neb.py --post-minimize --slip-systems edge_b100_p100_300K

# Process specific samples
python3 gpu_queue_manager_neb.py --neb-mode --samples sample1 sample2
python3 gpu_queue_manager_neb.py --post-minimize --samples sample1

# Custom NEB root directory
python3 gpu_queue_manager_neb.py --neb-mode --neb-root /path/to/your/neb
python3 gpu_queue_manager_neb.py --post-minimize --neb-root /path/to/your/neb
```

### Advanced Usage

```bash
# Process specific slip systems and samples with custom log file
python3 gpu_queue_manager_neb.py \
    --neb-mode \
    --slip-systems edge_b100_p100_300K screw_b100_p100_300K \
    --samples sample1 \
    --log-file /path/to/custom.log

# Run in background with nohup
nohup python3 gpu_queue_manager_neb.py --neb-mode > gpu_queue.out 2>&1 &
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--neb-root` | Root directory of NEB pipeline | `neb` (this folder) |
| `--slip-systems` | Specific slip systems to process | All available |
| `--samples` | Specific samples to process | All available |
| `--neb-mode` | Enable NEB mode for processing neb_*.data files | False |
| `--post-minimize` | Enable post-minimize mode for processing neb_*.data files | False |
| `--log-file` | Custom log file path | `neb_root/gpu_queue.log` |

## How It Works

### 1. GPU Detection
The script automatically detects available GPUs:
- **A100 GPUs**: 0-3 (if available)
- **V100 GPUs**: 4-7 (if available)
- **Job Limits**: 4 A100 jobs, 4 V100 jobs (or 8 V100 jobs if no A100)

### 2. Task Scanning
The script scans for NEB tasks in the following order:
1. All slip system directories (`edge_*`, `screw_*`)
2. All sample directories (`sample*`)
3. All `neb_*.data` files in each sample directory

### 3. Task Processing

#### NEB Mode
For each `neb_*.data` file:
1. Creates a LAMMPS input file (`in.neb_<neb_name>`)
2. Assigns to an available GPU
3. Runs minimization using appropriate LAMMPS executable
4. Monitors completion and extracts final energy

#### Post-Minimize Mode
For each directory containing `neb_*.data` files:
1. Creates a `minimize/` directory
2. For each `neb_*.data` file:
   - Creates a subdirectory `minimize/neb_X/`
   - Copies the NEB file and SNAP files
   - Creates minimize input file (`in.min`)
   - Runs minimization
3. Extracts energies from all completed minimizations
4. Creates an energy plot (`energy_plot.png`)

### 4. Next Folder Support
The script automatically scans for `next_*` folders under sample directories and processes them the same way as regular sample directories. This allows processing of refinement iterations created by the NEB pipeline.

### 5. Energy Extraction and Plotting
- **NEB Mode**: Extracts final energies and saves to `final_energies.csv`
- **Post-Minimize Mode**: Extracts energies, normalizes them, and creates energy path plots

## Output Files

### Log File
- **Location**: `neb_root/gpu_queue.log` (or custom path)
- **Content**: Detailed logging of all operations, job status, and errors

### Final Energies
- **Location**: `neb_root/final_energies.csv`
- **Format**: CSV with columns `neb_name,final_energy`
- **Content**: Final energies for all completed NEB tasks

### NEB Input Files
- **Location**: `slip_system/sample/in.neb_<neb_name>`
- **Content**: LAMMPS input files for NEB minimization

### STDOUT Files
- **Location**: `slip_system/sample/stdout_<neb_name>`
- **Content**: LAMMPS output for each NEB task

## Monitoring and Status

### Real-time Status
The script displays real-time status information:
```
Status: A100 jobs: 2/4, V100 jobs: 1/4
```

### Log Messages
Key log messages to watch for:
- `Starting NEB minimization for <neb_name> on GPU <gpu_id>`
- `SUCCESS: NEB task <neb_name> completed successfully`
- `WARNING: NEB task <neb_name> finished but energy extraction failed`

## Troubleshooting

### Common Issues

1. **No GPUs detected**:
   ```
   Could not detect GPU configuration
   ```
   - Check if `nvidia-smi` is available
   - Verify GPU drivers are installed

2. **SNAP files not found**:
   ```
   ERROR: SNAP coefficient file not found
   ```
   - Verify SNAP files exist in `pe/` directory
   - Check file permissions

3. **LAMMPS executable not found**:
   ```
   FileNotFoundError: [Errno 2] No such file or directory: 'lmp_kokkos_cuda_*'
   ```
   - Update LAMMPS executable paths in the script
   - Verify LAMMPS is installed

4. **Permission denied**:
   ```
   PermissionError: [Errno 13] Permission denied
   ```
   - Check file permissions
   - Ensure write access to NEB directory

### Debug Mode

To enable more verbose logging, modify the logging level in the script:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## Performance Optimization

### GPU Utilization
- The script automatically balances load between A100 and V100 GPUs
- Jobs are assigned based on availability and limits
- Monitor GPU utilization with `nvidia-smi`

### Memory Management
- GPUs are considered available if utilization < 10% and memory < 1000MB
- Adjust thresholds in `is_gpu_available()` method if needed

### Parallel Processing
- Multiple NEB tasks can run simultaneously
- Limited by available GPUs and job limits
- Consider system resources when setting limits

## Integration with NEB Pipeline

### Before Running
1. Ensure NEB pipeline has generated `neb_*.data` files
2. Verify all required files are in place
3. Check GPU availability

### After Running
1. Check `final_energies.csv` for extracted energies
2. Review log file for any errors
3. Verify all expected tasks completed

### Integration with Post-NEB Analysis
The extracted energies can be used with the existing NEB pipeline's post-processing tools:
```bash
# Use extracted energies for analysis
python3 run_neb_pipeline.py --post-minimize --slip edge_b100_p100_300K --sample sample1
```

## Best Practices

1. **Run during off-peak hours** to maximize GPU availability
2. **Monitor log files** regularly for errors
3. **Backup important data** before running large batches
4. **Test with small subsets** before processing all data
5. **Use specific slip systems/samples** to avoid unnecessary processing

## Example Workflow

```bash
# 1. Check available slip systems
ls -d edge_* screw_*

# 2. Run GPU queue manager for specific slip system
python3 gpu_queue_manager_neb.py \
    --neb-mode \
    --slip-systems edge_b100_p100_300K \
    --samples sample1

# 3. Monitor progress
tail -f gpu_queue.log

# 4. Check results
cat final_energies.csv

# 5. Continue with post-processing
python3 run_neb_pipeline.py --post-minimize \
    --slip edge_b100_p100_300K --sample sample1
```

## Support

For issues or questions:
1. Check the log file for error messages
2. Verify all dependencies are installed
3. Test with a small subset first
4. Review the troubleshooting section above
