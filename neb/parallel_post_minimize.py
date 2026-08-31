#!/usr/bin/env python3
"""
并行 Post-NEB Minimize 脚本
用于快速处理所有 slip systems 的 post-minimize
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

# 配置
SCRIPT_DIR = Path(__file__).parent.resolve()
SNAP_COEFF = SCRIPT_DIR / "../potentials/HEA_v3_trial3.snapcoeff"
SNAP_PARAM = SCRIPT_DIR / "../potentials/HEA_v3_trial3.snapparam"
LAMMPS_EXE = Path("/home/u6710794/lammps-stable_29Aug2024_update3/src/lmp_intel_cpu_intelmpi")

# Slip systems
SLIP_SYSTEMS = [
    'edge_b100_p100_300K',
    'edge_b100_p110_300K', 
    'edge_b111_p110_300K',
    'screw_b100_100_300K',
    'screw_b100_p110_300K',
    'screw_b111_p110_330K',
]

def get_neb_files(work_dir: Path) -> List[Path]:
    """获取所有 neb_*.data 文件"""
    neb_files = list(work_dir.glob("neb_*.data"))
    neb_files.sort(key=lambda p: int(p.stem.split('_')[1]))
    return neb_files

def create_minimize_input(neb_data: Path, output_dir: Path) -> Path:
    """创建 in.min 文件"""
    template = f"""atom_style      atomic
units           metal
boundary        p p p
read_data       {neb_data.name}

mass     1 58.6934
mass     2 58.933195
mass     3 47.867
mass     4 91.224
mass     5 178.49

pair_style      snap
pair_coeff      * * {SNAP_COEFF} {SNAP_PARAM} Ni Co Ti Zr Hf

# Boundary condition setup
variable	upp_zhi equal bound(all,zmax)+1
variable	upp_zlo equal ${{upp_zhi}}-4.0
variable	bot_zlo equal bound(all,zmin)-1
variable	bot_zhi equal ${{bot_zlo}}+4.0

# Constraint setup
region		fix_upp block EDGE EDGE EDGE EDGE ${{upp_zlo}} ${{upp_zhi}} units box
region		fix_bot block EDGE EDGE EDGE EDGE ${{bot_zlo}} ${{bot_zhi}} units box
region		constrain union 2 fix_upp fix_bot
group		constrain region constrain
group	    mobile subtract all constrain
fix		f constrain setforce NULL NULL 0

# Minimization
minimize	0.0 0.05 5000 1000
"""
    
    output_file = output_dir / "in.min"
    with open(output_file, 'w') as f:
        f.write(template)
    
    return output_file

def run_single_minimize(neb_data: Path, work_dir: Path, cores: int = 64, 
                       local_mode: bool = False, account: str = "MST114385") -> bool:
    """运行单个 neb_*.data 的 minimize"""
    neb_name = neb_data.stem
    
    # 创建 minimize 目录
    minimize_dir = work_dir / "minimize" / neb_name
    minimize_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制数据文件
    import shutil
    shutil.copy(neb_data, minimize_dir / neb_data.name)
    
    # 创建输入文件
    create_minimize_input(neb_data, minimize_dir)
    
    # 运行 minimize
    if local_mode:
        command = f"mpirun -np {cores} {LAMMPS_EXE} -in in.min"
        try:
            result = subprocess.run(command, shell=True, cwd=minimize_dir, 
                                  capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                print(f"✓ {neb_name} completed")
                return True
            else:
                print(f"✗ {neb_name} failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print(f"✗ {neb_name} timed out")
            return False
    else:
        # SLURM 模式
        slurm_script = f"""#!/bin/bash
#SBATCH --account={account}
#SBATCH --job-name=min_{neb_name}
#SBATCH --partition=ct112
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --ntasks-per-node={cores}
#SBATCH --output=job-%j.out
#SBATCH --error=job-%j.err

module purge
module load intel/2023_2

mpiexec -np {cores} {LAMMPS_EXE} -in in.min > STDOUT_min
"""
        
        script_path = minimize_dir / f"submit_min_{neb_name}.sh"
        with open(script_path, 'w') as f:
            f.write(slurm_script)
        
        try:
            result = subprocess.run(['sbatch', str(script_path)], 
                                  cwd=minimize_dir, capture_output=True, text=True)
            if result.returncode == 0:
                job_id = result.stdout.strip().split()[-1]
                print(f"✓ {neb_name} submitted (job {job_id})")
                
                # 等待作业完成
                while True:
                    result = subprocess.run(['squeue', '-j', job_id], 
                                          capture_output=True, text=True)
                    if job_id not in result.stdout:
                        break
                    time.sleep(10)
                
                # 检查结果
                stdout_file = minimize_dir / "STDOUT_min"
                if stdout_file.exists() and "Total wall time:" in stdout_file.read_text():
                    print(f"✓ {neb_name} completed")
                    return True
                else:
                    print(f"✗ {neb_name} failed")
                    return False
            else:
                print(f"✗ {neb_name} submission failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"✗ {neb_name} error: {e}")
            return False

def process_slip_system(slip_system: str, sample: str = "sample1", 
                       cores: int = 64, max_parallel: int = 6,
                       local_mode: bool = False, account: str = "MST114385") -> Tuple[bool, str]:
    """处理单个 slip system"""
    work_dir = SCRIPT_DIR / slip_system / sample
    
    if not work_dir.exists():
        return False, f"Directory not found: {work_dir}"
    
    # 检查是否已有 minimize 目录
    minimize_dir = work_dir / "minimize"
    if minimize_dir.exists():
        return True, f"Skipped (minimize exists): {slip_system}/{sample}"
    
    # 获取 neb 文件
    neb_files = get_neb_files(work_dir)
    if not neb_files:
        return False, f"No neb_*.data files found: {slip_system}/{sample}"
    
    print(f"\n{'─'*60}")
    print(f"Processing: {slip_system}/{sample}")
    print(f"Found {len(neb_files)} neb_*.data files")
    print(f"Running {min(max_parallel, len(neb_files))} minimize jobs in parallel...")
    print(f"{'─'*60}")
    
    # 并行处理
    success_count = 0
    with ThreadPoolExecutor(max_workers=min(max_parallel, len(neb_files))) as executor:
        future_to_file = {
            executor.submit(run_single_minimize, neb_file, work_dir, cores, 
                           local_mode, account): neb_file
            for neb_file in neb_files
        }
        
        for future in as_completed(future_to_file):
            neb_file = future_to_file[future]
            try:
                success = future.result()
                if success:
                    success_count += 1
            except Exception as e:
                print(f"✗ {neb_file.name} failed with exception: {e}")
    
    print(f"Successfully minimized {success_count}/{len(neb_files)} files")
    return success_count == len(neb_files), f"Completed: {slip_system}/{sample}"

def main():
    parser = argparse.ArgumentParser(description="Parallel Post-NEB Minimize")
    parser.add_argument("--slip", help="Specific slip system to process")
    parser.add_argument("--sample", default="sample1", help="Sample name")
    parser.add_argument("--cores", type=int, default=64, help="Cores per minimize job")
    parser.add_argument("--parallel", type=int, default=6, help="Max parallel jobs per slip system")
    parser.add_argument("--local", action="store_true", help="Run locally")
    parser.add_argument("--account", default="MST114385", help="SLURM account")
    
    args = parser.parse_args()
    
    if args.slip:
        slip_systems = [args.slip]
    else:
        slip_systems = SLIP_SYSTEMS
    
    print(f"\n{'='*60}")
    print("PARALLEL POST-NEB MINIMIZE")
    print(f"{'='*60}")
    print(f"Slip systems: {len(slip_systems)}")
    print(f"Cores per job: {args.cores}")
    print(f"Max parallel: {args.parallel}")
    print(f"Mode: {'Local' if args.local else 'SLURM'}")
    print(f"{'='*60}\n")
    
    successes = []
    failures = []
    
    for slip_system in slip_systems:
        success, message = process_slip_system(
            slip_system, args.sample, args.cores, 
            args.parallel, args.local, args.account
        )
        
        if success:
            successes.append(message)
        else:
            failures.append(message)
    
    # 总结
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total: {len(slip_systems)}")
    print(f"Successful: {len(successes)}")
    print(f"Failed: {len(failures)}")
    
    if successes:
        print(f"\n✓ SUCCESSFUL:")
        for msg in successes:
            print(f"  {msg}")
    
    if failures:
        print(f"\n✗ FAILED:")
        for msg in failures:
            print(f"  {msg}")
    
    print(f"\n{'='*60}")

if __name__ == "__main__":
    main()


