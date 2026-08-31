#!/usr/bin/env python3
"""
NEB Pipeline for Edge and Screw Dislocations
Workflow: build -> minimize -> align -> gen_aligned -> in.min -> in.neb
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# =============================
# Configuration
# =============================

# Use relative paths
SCRIPT_DIR = Path(__file__).parent.resolve()
SNAP_COEFF = SCRIPT_DIR / "../potentials/HEA_v3_trial3.snapcoeff"
SNAP_PARAM = SCRIPT_DIR / "../potentials/HEA_v3_trial3.snapparam"
STANDARD_MODEL_DIR = SCRIPT_DIR / "standard_model"

# LAMMPS executable (update if needed)
LAMMPS_EXE = Path("/home/u6710794/lammps-stable_29Aug2024_update3")
LAMMPS_EXE_LOCAL = Path.home() / "Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100"

# Slip system mapping: slip_system_name -> (type, orientation)
SLIP_SYSTEM_MAPPING = {
    'edge_b100_p100_300K': ('edge', 'b100_p100'),
    'edge_b100_p110_300K': ('edge', 'b100_p110'),
    'edge_b111_p110_300K': ('edge', 'b111_p110'),
    'screw_b100_100_300K': ('screw', 'b100_p100'),
    'screw_b100_p110_300K': ('screw', 'b100_p110'),
    'screw_b111_p110_300K': ('screw', 'b111_p110'),
}

# Parallel execution settings
DEFAULT_MAX_WORKERS = 6  # Default number of parallel slip systems

# SLURM partition selection based on core count
def select_partition(cores: int) -> str:
    """Select appropriate SLURM partition based on core count."""
    if cores <= 112:
        return "ct112"
    elif cores <= 448:
        return "ct448"
    elif cores <= 1120:
        return "ct1k"
    elif cores <= 2240:
        return "ct2k"
    elif cores <= 4480:
        return "ct4k"
    else:
        return "ct8k"


def calculate_optimal_workers(align_np: int = 64, min_np: int = 64, neb_np: int = 168) -> int:
    """
    Calculate optimal number of parallel workers based on core requirements.
    
    Args:
        align_np: Cores needed for align step
        min_np: Cores needed for minimize step  
        neb_np: Cores needed for NEB step (highest requirement)
    
    Returns:
        Maximum number of parallel workers that fit in available partitions
    """
    # Get the maximum cores needed per pipeline
    max_cores_per_pipeline = max(align_np, min_np, neb_np)
    
    # Calculate how many pipelines can run in parallel for each partition
    partition_capacities = {
        "ct112": 112,
        "ct448": 448, 
        "ct1k": 1120,
        "ct2k": 2240,
        "ct4k": 4480,
        "ct8k": 8960
    }
    
    # We want to run 6 pipelines in parallel, so we need 6 * 168 = 1008 cores
    # Find the smallest partition that can handle this
    required_cores = 6 * max_cores_per_pipeline  # 6 * 168 = 1008
    
    for partition, capacity in partition_capacities.items():
        if capacity >= required_cores:
            # This partition can handle 6 pipelines
            return 6
    
    # If no partition can handle 6 pipelines, return the maximum possible
    # Find the partition that can handle the most pipelines
    max_workers = 0
    for partition, capacity in partition_capacities.items():
        workers = capacity // max_cores_per_pipeline
        max_workers = max(max_workers, workers)
    
    return min(max_workers, 6)  # Maximum 6 parallel pipelines


def run_single_pipeline(slip_system: str, sample: str, account: str, skip_build: bool, local: bool) -> Tuple[bool, str, str]:
    """
    Run a single pipeline and return results.
    
    Returns:
        (success, slip_system, message)
    """
    try:
        print(f"\n{'='*40}")
        print(f"Starting {slip_system}/{sample}")
        print(f"{'='*40}")
        
        run_pipeline(slip_system, sample, account, skip_build, local)
        
        success_msg = f"✓ {slip_system}/{sample} completed successfully"
        print(success_msg)
        return True, slip_system, success_msg
        
    except Exception as e:
        error_msg = f"✗ {slip_system}/{sample} failed: {e}"
        print(error_msg)
        return False, slip_system, error_msg


# =============================
# Helper Functions
# =============================

def read_lattice_params(after_relax_path: Path) -> Tuple[float, float, float]:
    """
    Read lattice parameters from after_relax_bulk.data lines 6-8.
    Returns: (bulk_lx, bulk_ly, bulk_lz)
    """
    with open(after_relax_path, 'r') as f:
        lines = f.readlines()
    
    # Line 6: xlo xhi
    xlo, xhi = map(float, lines[5].split()[:2])
    bulk_lx = xhi - xlo
    
    # Line 7: ylo yhi
    ylo, yhi = map(float, lines[6].split()[:2])
    bulk_ly = yhi - ylo
    
    # Line 8: zlo zhi
    zlo, zhi = map(float, lines[7].split()[:2])
    bulk_lz = zhi - zlo
    
    return bulk_lx, bulk_ly, bulk_lz


def modify_build_file(
    template_path: Path,
    output_path: Path,
    standard_model_path: Path,
    bulk_lx: float,
    bulk_ly: float,
    bulk_lz: float,
    dislocation_type: str
):
    """
    Modify in.build_edge or in.build_screw file:
    1. Update read_data path to point to standard_model
    2. Update pair_coeff to use relative SNAP paths
    3. Update bulk lattice parameters (replicated values)
    """
    with open(template_path, 'r') as f:
        lines = f.readlines()
    
    # Determine replicate based on file content
    replicate_line = None
    for i, line in enumerate(lines):
        if line.strip().startswith('replicate'):
            replicate_line = line.strip()
            break
    
    # Extract replicate factors
    if replicate_line:
        parts = replicate_line.split()
        rx, ry, rz = int(parts[1]), int(parts[2]), int(parts[3])
    else:
        rx, ry, rz = 4, 1, 4  # default
    
    # Calculate bulk values (considering replicate)
    bulk_lx_val = bulk_lx * rx
    bulk_ly_val = bulk_ly * ry
    bulk_lz_val = bulk_lz * rz
    
    modified_lines = []
    for i, line in enumerate(lines, start=1):
        # Update read_data paths
        if line.strip().startswith('read_data'):
            rel_path = os.path.relpath(standard_model_path, output_path.parent)
            modified_lines.append(f"read_data       {rel_path}\n")
        # Update pair_coeff paths
        elif 'pair_coeff' in line and 'snap' in lines[i-2].lower():
            rel_coeff = os.path.relpath(SNAP_COEFF, output_path.parent)
            rel_param = os.path.relpath(SNAP_PARAM, output_path.parent)
            modified_lines.append(f"pair_coeff      * * {rel_coeff} {rel_param} Ni Co Ti Zr Hf\n")
        # Update bulk lattice parameters - match any line with "variable bulk_lx/ly/lz equal"
        elif 'variable' in line and 'bulk_lx' in line and 'equal' in line:
            modified_lines.append(f"variable        bulk_lx equal {bulk_lx_val:.10f}\n")
        elif 'variable' in line and 'bulk_ly' in line and 'equal' in line:
            modified_lines.append(f"variable        bulk_ly equal {bulk_ly_val:.10f}\n")
        elif 'variable' in line and 'bulk_lz' in line and 'equal' in line:
            modified_lines.append(f"variable        bulk_lz equal {bulk_lz_val:.10f}\n")
        else:
            modified_lines.append(line)
    
    with open(output_path, 'w') as f:
        f.writelines(modified_lines)


def modify_in_min(template_path: Path, output_path: Path):
    """Update pair_coeff paths in in.min to use relative paths."""
    with open(template_path, 'r') as f:
        lines = f.readlines()
    
    modified_lines = []
    for line in lines:
        if 'pair_coeff' in line and '.snap' in line:
            rel_coeff = os.path.relpath(SNAP_COEFF, output_path.parent)
            rel_param = os.path.relpath(SNAP_PARAM, output_path.parent)
            modified_lines.append(f"pair_coeff      * * {rel_coeff} {rel_param} Ni Co Ti Zr Hf\n")
        else:
            modified_lines.append(line)
    
    with open(output_path, 'w') as f:
        f.writelines(modified_lines)


def modify_in_neb(template_path: Path, output_path: Path, u_value: int = 21):
    """Update in.neb file: set u uloop value and fix pair_coeff paths."""
    with open(template_path, 'r') as f:
        lines = f.readlines()
    
    modified_lines = []
    for line in lines:
        if 'variable' in line and 'u uloop' in line:
            modified_lines.append(f"variable        u uloop {u_value}\n")
        elif 'pair_coeff' in line and '.snap' in line:
            rel_coeff = os.path.relpath(SNAP_COEFF, output_path.parent)
            rel_param = os.path.relpath(SNAP_PARAM, output_path.parent)
            modified_lines.append(f"pair_coeff      * * {rel_coeff} {rel_param} Ni Co Ti Zr Hf\n")
        else:
            modified_lines.append(line)
    
    with open(output_path, 'w') as f:
        f.writelines(modified_lines)


def process_final_cfg(work_dir: Path) -> bool:
    """
    Process final.cfg:
    1. Remove lines 1-3 and 5-9
    2. Save as final.txt
    Returns True if successful.
    """
    final_cfg = work_dir / "final.cfg"
    final_txt = work_dir / "final.txt"
    
    if not final_cfg.exists():
        return False
    
    with open(final_cfg, 'r') as f:
        lines = f.readlines()
    
    # Remove lines 1-3 (indices 0-2) and lines 5-9 (indices 4-8)
    kept_lines = []
    for i, line in enumerate(lines, start=1):
        if i in [1, 2, 3, 5, 6, 7, 8, 9]:
                continue
        kept_lines.append(line)
    
    with open(final_txt, 'w') as f:
        f.writelines(kept_lines)
    
    return True


def submit_slurm_job(
    work_dir: Path,
    job_name: str,
    cores: int,
    command: str,
    account: str = "MST114385"
) -> Optional[str]:
    """
    Submit a SLURM job and return the job ID.
    """
    # Check if sbatch is available
    try:
        result = subprocess.run(['which', 'sbatch'], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("sbatch command not found. Please use --local mode or run on a system with SLURM.")
    except FileNotFoundError:
        raise RuntimeError("sbatch command not found. Please use --local mode or run on a system with SLURM.")
    
    partition = select_partition(cores)
    
    # Calculate nodes and tasks per node
    if cores <= 112:
        nodes = 1
        ntasks_per_node = cores
    else:
        ntasks_per_node = 112
        nodes = (cores + ntasks_per_node - 1) // ntasks_per_node
    
    slurm_script = f"""#!/bin/bash
#SBATCH --account={account}
#SBATCH --job-name={job_name}
#SBATCH --partition={partition}
#SBATCH --nodes={nodes}
#SBATCH --cpus-per-task=1
#SBATCH --ntasks-per-node={ntasks_per_node}
#SBATCH --output=job-%j.out
#SBATCH --error=job-%j.err

module purge
module load intel/2023_2

{command}
"""
    
    script_path = work_dir / f"submit_{job_name}.sh"
    with open(script_path, 'w') as f:
        f.write(slurm_script)
    
    # Submit job
    result = subprocess.run(
        ['sbatch', str(script_path)],
        cwd=work_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error submitting job: {result.stderr}")
        return None
    
    # Extract job ID
    match = re.search(r'Submitted batch job (\d+)', result.stdout)
    if match:
        return match.group(1)
    return None


def wait_for_job(job_id: str, check_interval: int = 60):
    """Wait for a SLURM job to complete."""
    print(f"Waiting for job {job_id} to complete...")
    while True:
        result = subprocess.run(
            ['squeue', '-j', job_id, '-h'],
            capture_output=True,
            text=True
        )
        
        if not result.stdout.strip():
            # Job no longer in queue
            print(f"Job {job_id} completed.")
            break
        
        time.sleep(check_interval)


def run_local_job(
    work_dir: Path,
    job_name: str,
    command: str,
    use_nohup: bool = True
) -> int:
    """
    Run a job locally (not through SLURM) using nohup and mpirun.
    Returns the process return code.
    """
    print(f"Running {job_name} locally...")
    
    # Prepare output files - use STDOUT naming convention
    output_file = work_dir / f"STDOUT_{job_name}"
    error_file = work_dir / f"STDERR_{job_name}"
    
    if use_nohup:
        # Use nohup to run in background
        # Write PID to file for monitoring
        pid_file = work_dir / f"{job_name}_local.pid"
        full_command = f"cd {work_dir} && nohup {command} > {output_file} 2> {error_file} & echo $! > {pid_file}"
        result = subprocess.run(
            full_command,
            shell=True,
                stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            print(f"  Job {job_name} started in background")
            print(f"  Output: {output_file}")
            print(f"  Error: {error_file}")
            
            # Read the PID
            time.sleep(2)
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                print(f"  PID: {pid}")
            except:
                print(f"  WARNING: Could not read PID file")
                pid = None
            
            # Wait for the job to complete by checking if the process is still running
            print(f"  Waiting for {job_name} to complete...")
            check_count = 0
            while True:
                if pid:
                    # Check if process is still running
                    try:
                        os.kill(pid, 0)  # Signal 0 just checks if process exists
                        # Process is still running
                        if check_count % 6 == 0:  # Print every minute
                            print(f"  Job {job_name} still running... (PID {pid})")
                        check_count += 1
                        time.sleep(10)
                    except OSError:
                        # Process has terminated
                        print(f"  Job {job_name} completed (PID {pid} terminated)")
                        break
                    else:
                        # Fallback to file size monitoring (less reliable)
                        if output_file.exists():
                            current_size = output_file.stat().st_size
                            print(f"  Output file size: {current_size} bytes")
                        time.sleep(30)
                        # For jobs without PID, wait longer before checking
                        check_count += 1
                        if check_count >= 10:  # Wait at least 5 minutes
                            break
            
            print(f"  Job {job_name} monitoring completed")
            return 0
        else:
            print(f"  Failed to start {job_name}: {result.stderr}")
            return result.returncode
    else:
        # Run in foreground
        result = subprocess.run(
            command,
            shell=True,
            cwd=work_dir,
            capture_output=False,
            text=True
        )
        return result.returncode


def check_gen_aligned_success(work_dir: Path) -> bool:
    """
    Check if gen_aligned_structure completed successfully by looking for
    displacement output in STDOUT.
    """
    # Check STDOUT_gen first (for both local and SLURM modes)
    stdout_gen = work_dir / "STDOUT_gen"
    if stdout_gen.exists() and stdout_gen.stat().st_size > 0:
        with open(stdout_gen, 'r') as f:
            content = f.read()
        return "Orginal Total Displacement:" in content and "New Total Displacement:" in content
    
    # Fallback to SLURM job files
    output_files = list(work_dir.glob("job-*.out"))
    if output_files:
        latest_job = max(output_files, key=lambda p: p.stat().st_mtime)
        with open(latest_job, 'r') as f:
            content = f.read()
        return "Orginal Total Displacement:" in content and "New Total Displacement:" in content
    
    return False


def check_in_neb_complete(work_dir: Path) -> bool:
    """
    Check if in.neb completed by looking for "Total wall time:" in stdout/screen files.
    """
    # Check STDOUT_neb first (for both local and SLURM modes)
    stdout_neb = work_dir / "STDOUT_neb"
    if stdout_neb.exists() and stdout_neb.stat().st_size > 0:
        with open(stdout_neb, 'r') as f:
            lines = f.readlines()
        # Check last 10 lines
        for line in lines[-10:]:
            if "Total wall time:" in line:
                return True
    
    # Check other possible output files
    for filename in ["STDOUT2", "screen", "log.lammps", "job-*.out"]:
        if "*" in filename:
            files = list(work_dir.glob(filename))
            if files:
                filepath = max(files, key=lambda p: p.stat().st_mtime)
            else:
                continue
        else:
            filepath = work_dir / filename
        
        if filepath.exists() and filepath.stat().st_size > 0:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            # Check last 10 lines
            for line in lines[-10:]:
                if "Total wall time:" in line:
                    return True
    
    return False


# =============================
# Main Pipeline Functions
# =============================

def setup_work_directory(
    slip_system: str,
    sample: str,
    dislocation_type: str,
    orientation: str
) -> Tuple[Path, Path, Path]:
    """
    Set up work directory and get paths.
    Returns: (work_dir, standard_model_path, after_relax_path)
    """
    work_dir = SCRIPT_DIR / slip_system / sample
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # Get standard model path
    standard_model_path = STANDARD_MODEL_DIR / sample / orientation / "HEA_init.data"
    after_relax_path = STANDARD_MODEL_DIR / sample / orientation / "relax_300K" / "after_relax_bulk.data"
    
    if not standard_model_path.exists():
        raise FileNotFoundError(f"Standard model not found: {standard_model_path}")
    if not after_relax_path.exists():
        raise FileNotFoundError(f"after_relax_bulk.data not found: {after_relax_path}")
    
    return work_dir, standard_model_path, after_relax_path


def run_pipeline(
    slip_system: str,
    sample: str,
    account: str = "MST114385",
    skip_build: bool = False,
    local: bool = False
):
    """
    Run the complete NEB pipeline for a given slip_system and sample.
    
    Workflow:
    1. Build structures (in.build_edge or in.build_screw)
    2. Minimize (in.min for HEA_init structures)
    3. Align (align_mpi_edge or align_mpi_screw) - 64 cores
    4. Generate aligned structure (gen_aligned_structure)
    5. Minimize aligned structures (in.min) - 64 cores
    6. NEB calculation (in.neb) - 168 cores (21x8 partition)
    
    Args:
        local: If True, run locally without SLURM (for testing on amd01)
    """
    print(f"\n{'='*60}")
    print(f"Starting pipeline for {slip_system}/{sample}")
    if local:
        print("Mode: LOCAL (no SLURM)")
    else:
        print("Mode: SLURM")
    print(f"{'='*60}\n")
    
    # Get slip system info
    if slip_system not in SLIP_SYSTEM_MAPPING:
        raise ValueError(f"Unknown slip system: {slip_system}")
    
    dislocation_type, orientation = SLIP_SYSTEM_MAPPING[slip_system]
    
    # Setup directories
    work_dir, standard_model_path, after_relax_path = setup_work_directory(
        slip_system, sample, dislocation_type, orientation
    )
    
    # Read lattice parameters
    bulk_lx, bulk_ly, bulk_lz = read_lattice_params(after_relax_path)
    print(f"Lattice parameters: lx={bulk_lx:.4f}, ly={bulk_ly:.4f}, lz={bulk_lz:.4f}")
    
    # Select LAMMPS executable based on mode
    lammps_exe = LAMMPS_EXE_LOCAL if local else LAMMPS_EXE
    print(f"LAMMPS executable: {lammps_exe}")
    
    # =============================
    # Step 1: Build structures
    # =============================
    if not skip_build:
        print("\n[Step 1] Building structures...")
        
        build_file = f"in.build_{dislocation_type}"
        template_build = SCRIPT_DIR / build_file
        output_build = work_dir / build_file
        
        modify_build_file(
            template_build, output_build, standard_model_path,
            bulk_lx, bulk_ly, bulk_lz, dislocation_type
        )
        
        # Copy align and gen_aligned scripts
        align_script = SCRIPT_DIR / f"align_mpi_{dislocation_type}.py"
        shutil.copy2(align_script, work_dir / "align_mpi.py")
        shutil.copy2(SCRIPT_DIR / "gen_aligned_structure.py", work_dir / "gen_aligned_structure.py")
        
        # Modify gen_aligned_structure.py for correct file names
        gen_script = work_dir / "gen_aligned_structure.py"
        with open(gen_script, 'r') as f:
            content = f.read()
        
        if dislocation_type == 'screw':
            content = content.replace('HEA_init_edge1.data', 'HEA_init_screw1.data')
            content = content.replace('HEA_init_edge2.data', 'HEA_init_screw2.data')
            content = content.replace('HEA_init_edge3.data', 'HEA_init_screw3.data')
        
        with open(gen_script, 'w') as f:
            f.write(content)
        
        # Submit build job (using 64 cores for local mode)
        if local:
            command = f"mpirun -np 64 {lammps_exe} -in {build_file}"
            rc = run_local_job(work_dir, "build", command)
            if rc != 0:
                print("Failed to run build job locally")
                return
        else:
            command = f"mpiexec -np 1 {lammps_exe} -in {build_file} > STDOUT_build"
            job_id = submit_slurm_job(work_dir, f"build_{sample}", 1, command, account)

            if job_id:
                wait_for_job(job_id)
            else:
                print("Failed to submit build job")
                raise RuntimeError("Failed to submit build job")
        
    print("[Step 1] Build completed.")
    
    # =============================
    # Step 2: Align structures
    # =============================
    print("\n[Step 2] Aligning structures...")
    
    if local:
        command = f"mpirun -np 64 python3 align_mpi.py"
        rc = run_local_job(work_dir, "align", command)
        if rc != 0:
            print("Failed to run align job locally")
            return
    else:
        command = f"mpiexec -np 64 python3 align_mpi.py > STDOUT_align"
        job_id = submit_slurm_job(work_dir, f"align_{sample}", 64, command, account)
        
        if job_id:
            wait_for_job(job_id)
        else:
            print("Failed to submit align job")
            raise RuntimeError("Failed to submit align job")
    
    print("[Step 2] Align completed.")
    
    # =============================
    # Step 3: Generate aligned structure
    # =============================
    print("\n[Step 3] Generating aligned structure...")
    
    if local:
        command = f"python3 gen_aligned_structure.py"
        rc = run_local_job(work_dir, "gen", command, use_nohup=False)
        if rc != 0:
            print("Failed to run gen_aligned job locally")
            return
        
        # Check success
        if not check_gen_aligned_success(work_dir):
            print("WARNING: gen_aligned_structure may not have completed successfully")
    else:
        command = f"python3 gen_aligned_structure.py > STDOUT_gen"
        job_id = submit_slurm_job(work_dir, f"gen_{sample}", 1, command, account)
        
        if job_id:
            wait_for_job(job_id)
            
            # Check success
            if not check_gen_aligned_success(work_dir):
                print("WARNING: gen_aligned_structure may not have completed successfully")
            else:
                print("Failed to submit gen_aligned job")
            raise RuntimeError("Failed to submit gen_aligned job")
    
    print("[Step 3] Generate aligned completed.")
    
    # =============================
    # Step 4: Minimize (in.min)
    # =============================
    print("\n[Step 4] Running minimize (in.min)...")
    
    # Copy and modify in.min
    template_min = SCRIPT_DIR / "in.min"
    output_min = work_dir / "in.min"
    modify_in_min(template_min, output_min)
    
    # Modify in.min for correct file names if screw
    if dislocation_type == 'screw':
        with open(output_min, 'r') as f:
            content = f.read()
        content = content.replace('HEA_init_edge1.data', 'HEA_init_screw1.data')
        content = content.replace('HEA_init_edge3.data', 'HEA_init_screw3.data')
        content = content.replace('HEA_opt_edge1.data', 'HEA_opt_screw1.data')
        content = content.replace('HEA_opt_edge2.data', 'HEA_opt_screw2.data')
        with open(output_min, 'w') as f:
            f.write(content)
    
    if local:
        command = f"mpirun -np 64 {lammps_exe} -in in.min"
        rc = run_local_job(work_dir, "minimize", command)
        if rc != 0:
            print("Failed to run minimize job locally")
            return
        
        # Process final.cfg
        if process_final_cfg(work_dir):
            print("final.txt created successfully.")
        else:
            print("WARNING: final.cfg not found or processing failed")
    else:
        command = f"mpiexec -np 64 {lammps_exe} -in in.min > STDOUT_min"
        job_id = submit_slurm_job(work_dir, f"min_{sample}", 64, command, account)
        
        if job_id:
            wait_for_job(job_id)
            
            # Process final.cfg
            if process_final_cfg(work_dir):
                print("final.txt created successfully.")
            else:
                print("WARNING: final.cfg not found or processing failed")
        else:
            print("Failed to submit minimize job")
            raise RuntimeError("Failed to submit minimize job")
    
    print("[Step 4] Minimize completed.")
    
    # =============================
    # Step 5: NEB calculation
    # =============================
    print("\n[Step 5] Running NEB calculation...")
    
    # Copy and modify in.neb
    template_neb = SCRIPT_DIR / "in.neb"
    output_neb = work_dir / "in.neb"
    modify_in_neb(template_neb, output_neb, u_value=21)
    
    # Submit NEB job (using 64 cores for local mode, 168 cores for SLURM)
    if local:
        command = f"mpirun -np 64 {lammps_exe} -partition 8x8 -in in.neb"
        rc = run_local_job(work_dir, "neb", command)
        if rc != 0:
            print("Failed to run NEB job locally")
            return
        
        # Check completion
        if check_in_neb_complete(work_dir):
            print("NEB calculation completed successfully!")
        else:
            print("WARNING: NEB may not have completed successfully")
    else:
        command = f"mpiexec -np 168 {lammps_exe} -partition 21x8 -in in.neb > STDOUT_neb"
        job_id = submit_slurm_job(work_dir, f"neb_{sample}", 168, command, account)
        
        if job_id:
            wait_for_job(job_id)
            
            # Check completion
            if check_in_neb_complete(work_dir):
                print("NEB calculation completed successfully!")
            else:
                print("WARNING: NEB may not have completed successfully")
        else:
            print("Failed to submit NEB job")
            raise RuntimeError("Failed to submit NEB job")
    
    print("[Step 5] NEB completed.")
    
    print(f"\n{'='*60}")
    print(f"Pipeline completed for {slip_system}/{sample}")
    print(f"{'='*60}\n")


# =============================
# Main
# =============================

def main():
    parser = argparse.ArgumentParser(
        description="NEB Pipeline for Edge and Screw Dislocations"
    )
    parser.add_argument(
        "--slip",
        help="Slip system name (e.g., edge_b100_p100_300K)"
    )
    parser.add_argument(
        "--sample",
        help="Sample name (e.g., sample1)"
    )
    parser.add_argument(
        "--account",
        default="MST114385",
        help="SLURM account (default: MST114385)"
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip the build step (useful for rerunning)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run for all slip systems and samples"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run locally without SLURM (for testing on amd01, uses 64 cores)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers (auto-calculated if not specified)"
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Force sequential execution even for --all (disable parallel processing)"
    )
    parser.add_argument(
        "--post-minimize",
        action="store_true",
        help="Run post-NEB minimize after NEB completion (extract energies and plot)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.all:
        if not args.slip:
            parser.error("--slip is required when not using --all")
        if not args.sample:
            parser.error("--sample is required when not using --all")
    
    if args.all:
        # Run for all slip systems
        slip_systems = list(SLIP_SYSTEM_MAPPING.keys())
        
        if args.sequential or args.local:
            # Sequential execution (original behavior)
            print(f"Running {len(slip_systems)} slip systems sequentially...")
            for slip_system in slip_systems:
                try:
                    run_pipeline(slip_system, "sample1", args.account, args.skip_build, args.local)
                except Exception as e:
                    print(f"Error processing {slip_system}/sample1: {e}")
                continue
        else:
            # Parallel execution
            if args.workers is None:
                # Auto-calculate optimal workers based on core requirements
                args.workers = calculate_optimal_workers(align_np=64, min_np=64, neb_np=168)
            
            print(f"Running {len(slip_systems)} slip systems in parallel with {args.workers} workers...")
            print(f"Estimated cores per pipeline: 168 (NEB step)")
            print(f"Total estimated cores: {args.workers * 168}")
            print(f"Recommended partition: ct1k (1120 cores) or ct2k (2240 cores)")
            
            successes = []
            failures = []
            
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                # Submit all jobs
                future_to_slip = {
                    executor.submit(run_single_pipeline, slip_system, "sample1", args.account, args.skip_build, args.local): slip_system
                    for slip_system in slip_systems
                }
                
                # Process completed jobs
                for future in as_completed(future_to_slip):
                    slip_system = future_to_slip[future]
                    try:
                        success, slip_name, message = future.result()
                        if success:
                            successes.append((slip_name, message))
                        else:
                            failures.append((slip_name, message))
                    except Exception as e:
                        error_msg = f"✗ {slip_system} failed with exception: {e}"
                        failures.append((slip_system, error_msg))
            
            # Print summary
            print(f"\n{'='*60}")
            print("EXECUTION SUMMARY")
            print(f"{'='*60}")
            print(f"Total slip systems: {len(slip_systems)}")
            print(f"Successful: {len(successes)}")
            print(f"Failed: {len(failures)}")
            
            if successes:
                print(f"\n✓ SUCCESSFUL:")
                for slip_name, msg in successes:
                    print(f"  {msg}")
            
            if failures:
                print(f"\n✗ FAILED:")
                for slip_name, msg in failures:
                    print(f"  {msg}")
            
            print(f"{'='*60}")
            
            # Run post-minimize if requested
            if args.post_minimize and successes:
                print(f"\n{'='*60}")
                print("POST-NEB MINIMIZE (PARALLEL)")
                print(f"{'='*60}\n")
                print(f"Running post-minimize for {len(successes)} successful slip systems...")
                
                # Run parallel post-minimize for each successful slip system
                for slip_name, _ in successes:
                    slip_system = slip_name.split('/')[0]
                    print(f"\n{'─'*60}")
                    print(f"Post-minimizing: {slip_system}/sample1")
                    print(f"{'─'*60}")
                    
                    work_dir = SCRIPT_DIR / slip_system / "sample1"
                    
                    # Get all neb_*.data files
                    neb_files = list(work_dir.glob("neb_*.data"))
                    neb_files.sort(key=lambda p: int(p.stem.split('_')[1]))
                    
                    if not neb_files:
                        print(f"⊘ No neb_*.data files found in {slip_system}/sample1")
                        continue
                    
                    print(f"Found {len(neb_files)} neb_*.data files")
                    print(f"Running {min(6, len(neb_files))} minimize jobs in parallel...")
                    
                    # Determine slip type for energy normalization
                    if slip_system in SLIP_SYSTEM_MAPPING:
                        slip_type, _ = SLIP_SYSTEM_MAPPING[slip_system]
                    else:
                        slip_type = 'edge' if 'edge' in slip_system.lower() else 'screw'
                    
                    # Parallel minimize using external script
                    cmd = f"python3 {SCRIPT_DIR}/parallel_post_minimize.py --slip {slip_system} --sample sample1 --parallel 6"
                    if args.local:
                        cmd += " --local"
                    if args.account:
                        cmd += f" --account {args.account}"
                    
                    result = subprocess.run(cmd, shell=True, cwd=SCRIPT_DIR)
                    if result.returncode == 0:
                        print(f"✓ Post-minimize completed for {slip_system}")
                        print(f"  Energy plot: {slip_system}/sample1/minimize/energy_plot.png")
                    else:
                        print(f"✗ Post-minimize failed for {slip_system}")
                
                print(f"\n{'='*60}")
                print("POST-MINIMIZE COMPLETED")
                print(f"{'='*60}")
    else:
        run_pipeline(args.slip, args.sample, args.account, args.skip_build, args.local)
        
        # Run post-minimize if requested for single slip system
        if args.post_minimize:
            print(f"\n{'='*60}")
            print("POST-NEB MINIMIZE (PARALLEL)")
            print(f"{'='*60}\n")
            
            work_dir = SCRIPT_DIR / args.slip / args.sample
            
            # Get all neb_*.data files
            neb_files = list(work_dir.glob("neb_*.data"))
            if neb_files:
                neb_files.sort(key=lambda p: int(p.stem.split('_')[1]))
                print(f"Found {len(neb_files)} neb_*.data files")
                print(f"Running {min(6, len(neb_files))} minimize jobs in parallel...")
            
            # Run parallel post-minimize script
            cmd = f"python3 {SCRIPT_DIR}/parallel_post_minimize.py --slip {args.slip} --sample {args.sample} --parallel 6"
            if args.local:
                cmd += " --local"
            if args.account:
                cmd += f" --account {args.account}"
            
            result = subprocess.run(cmd, shell=True, cwd=SCRIPT_DIR)
            if result.returncode == 0:
                print(f"\n✓ Post-minimize completed")
                print(f"  Energy plot: {args.slip}/{args.sample}/minimize/energy_plot.png")
            else:
                print(f"✗ Post-minimize failed")


if __name__ == "__main__":
    main()