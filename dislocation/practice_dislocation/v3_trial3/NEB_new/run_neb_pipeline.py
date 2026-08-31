#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed


# =============================
# Constants and configuration
# =============================

REPO_ROOT = Path("dislocation/practice_dislocation/v3_trial3/NEB_new").resolve()

# SNAP potential absolute paths (fixed location per user preference)
SNAP_DIR = REPO_ROOT / "edge_b100_p100_NEB"
SNAP_COEFF = SNAP_DIR / "../../../../../potentials/HEA_v3_trial3.snapcoeff"
SNAP_PARAM = SNAP_DIR / "../../../../../potentials/HEA_v3_trial3.snapparam"

# LAMMPS executable absolute path
LAMMPS_EXE = Path("/home/jhenyu/lammps-stable_2Aug2023_update2/src/lmp_g++_openmpi")

# Reference inputs (templates)
REF_BUILD_EDGE = (
    REPO_ROOT
    / "edge_b100_p100_NEB/new/change_ratio_12_5_300K/in.build_edge"
)
REF_IN_MIN = (
    REPO_ROOT
    / "edge_b100_p100_NEB/new/change_ratio_12_5_300K/in.min"
)
REF_IN_NEB = (
    REPO_ROOT
    / "edge_b100_p100_NEB/new/change_ratio_12_5_300K/in.neb"
)

# Python utilities absolute paths (choose one canonical copy)
ALIGN_MPI_PY = (
    REPO_ROOT
    / "edge_b100_p100_NEB/new/change_ratio_20_300K/align_mpi.py"
)
GEN_ALIGNED_STRUCTURE_PY = (
    REPO_ROOT
    / "edge_b100_p100_NEB/new/change_ratio_20_300K/gen_aligned_structure.py"
)
ADJUST_SPECIES_PY = (
    REPO_ROOT
    / "edge_b100_p100_NEB/new/change_ratio_20_300K/adjust_species.py"
)

# Ratios and composition mapping (a-d confirmed by user)
RATIO_TO_COMPOSITION: Dict[str, Optional[Tuple[float, float, float]]] = {
    "12.5pct": (0.1875, 0.125, 0.1875),  # a)
    "16.7pct": None,  # b) skip adjust
    "20pct": (0.15, 0.2, 0.15),  # c)
    "25pct": (0.125, 0.25, 0.125),  # d)
}

# Default MPI settings (capped per user)
DEFAULT_ALIGN_NP = 64
DEFAULT_MIN_NP = 64
MAX_TOTAL_CORES = 256


class PipelineError(Exception):
    pass


@dataclass
class RunConfig:
    slip_system: str
    structure_choice: int
    x1: int
    x2: int
    align_np: int
    min_np: int
    email: Optional[str]

    @property
    def slip_dir(self) -> Path:
        return (REPO_ROOT / self.slip_system).resolve()


def ensure_paths() -> None:
    problems: List[str] = []
    for p in [SNAP_COEFF, SNAP_PARAM, LAMMPS_EXE, REF_BUILD_EDGE, REF_IN_MIN, REF_IN_NEB, ALIGN_MPI_PY, GEN_ALIGNED_STRUCTURE_PY, ADJUST_SPECIES_PY]:
        if not p.exists():
            problems.append(f"Missing required file: {p}")
    if problems:
        raise PipelineError("\n".join(problems))


def cap_cores(n: int) -> int:
    if n <= 0:
        return 1
    return min(n, MAX_TOTAL_CORES)


def prompt_if_none(value: Optional[str], prompt: str, choices: Optional[List[str]] = None) -> str:
    if value is not None:
        return value
    while True:
        user_input = input(prompt).strip()
        if not choices or user_input in choices:
            return user_input
        print(f"Please choose one of: {choices}")


def locate_structure_dir(slip_dir: Path, structure_choice: int) -> Path:
    # Primary: subdirs named structure1..structure5 under slip_dir
    candidate = slip_dir / f"structure{structure_choice}"
    if candidate.is_dir():
        return candidate
    # Secondary: slip_dir itself is already a structure dir (edge_b100_p110_NEB/structure1 bottom)
    # If slip_dir name already matches structure<id>, accept slip_dir
    if slip_dir.name == f"structure{structure_choice}":
        return slip_dir
    raise PipelineError(f"Cannot find structure{structure_choice} under {slip_dir}")


def find_perfect_b2_path(structure_dir: Path) -> Path:
    # Prefer .lmp, else .data
    for name in ["perfect_B2.lmp", "perfect_B2.data"]:
        p = structure_dir / name
        if p.exists():
            return p
    raise PipelineError(f"Neither perfect_B2.lmp nor perfect_B2.data found in {structure_dir}")


def copy_with_absolute_snap_paths(src_in_min: Path, dest_in_min: Path) -> None:
    text = src_in_min.read_text()
    # Replace pair_coeff line to use absolute SNAP paths
    text = re.sub(
        r"^pair_coeff\s+\*\s+\*\s+.*$",
        f"pair_coeff      * * {SNAP_COEFF} {SNAP_PARAM} Ni Co Ti Zr Hf",
        text,
        flags=re.MULTILINE,
    )
    dest_in_min.write_text(text)


def generate_in_build_edge(template_path: Path, output_path: Path, x1: int, x2: int) -> None:
    """
    Create a customized in.build_edge that:
    - reads perfect_B2_adjusted.lmp
    - uses absolute SNAP paths
    - parameterizes del_xlo/del_xhi using x1 for left block and x2 for right block
    - injects 'variable x1' and 'variable x2' declarations in both blocks

    Note: For left block we ensure xlo < xhi by setting:
      del_xlo = 0.5*lx - (x1+1)*full_bg - half_bg + 0.1
      del_xhi = 0.5*lx - x1*full_bg - half_bg + 0.1

    For right block:
      del_xlo = 0.5*lx + x2*full_bg + half_bg + 0.1
      del_xhi = 0.5*lx + (x2+1)*full_bg + half_bg + 0.1
    """
    original = template_path.read_text().splitlines()

    def replace_common(block_lines: List[str], side: str) -> List[str]:
        new_lines: List[str] = []
        for line in block_lines:
            if line.strip().startswith("read_data"):
                new_lines.append("read_data       perfect_B2_adjusted.lmp")
                continue
            if line.strip().startswith("pair_coeff"):
                new_lines.append(
                    f"pair_coeff      * * {SNAP_COEFF} {SNAP_PARAM} Ni Co Ti Zr Hf"
                )
                continue
            # pass through thermo and other lines
            if line.strip().startswith("thermo"):
                new_lines.append(line)
                # inject x1/x2 variable declarations right after thermo
                if side == "left":
                    new_lines.append(f"variable        x1 equal {x1}")
                else:
                    new_lines.append(f"variable        x2 equal {x2}")
                continue
            # Inject v_x1/v_x2 aliases right before first use to ensure defined
            if side == "left" and re.match(r"^\s*variable\s+full_bg\s+equal\b", line.replace("\t", " ")):
                new_lines.append("variable        v_x1 equal x1")
            if side == "right" and re.match(r"^\s*variable\s+full_bg\s+equal\b", line.replace("\t", " ")):
                new_lines.append("variable        v_x2 equal x2")

            # Robust match for variable del_xlo equal (tabs/spaces agnostic)
            if re.match(r"^\s*variable\s+del_xlo\s+equal\b", line.replace("\t", " ")):
                if side == "left":
                    new_lines.append(
                        "variable \tdel_xlo equal $(lx)*0.5-(v_x1+1)*${full_bg}-${half_bg}+0.1"
                    )
                else:
                    new_lines.append(
                        "variable \tdel_xlo equal $(lx)*0.5+v_x2*${full_bg}+${half_bg}+0.1"
                    )
                continue
            # Robust match for variable del_xhi equal (tabs/spaces agnostic)
            if re.match(r"^\s*variable\s+del_xhi\s+equal\b", line.replace("\t", " ")):
                if side == "left":
                    new_lines.append(
                        "variable \tdel_xhi equal $(lx)*0.5-v_x1*${full_bg}-${half_bg}+0.1"
                    )
                else:
                    new_lines.append(
                        "variable \tdel_xhi equal $(lx)*0.5+(v_x2+1)*${full_bg}+${half_bg}+0.1"
                    )
                continue
            new_lines.append(line)
        return new_lines

    # Split template into two blocks using the first write_data HEA_init_edge1.data as separator
    try:
        idx_write1 = next(
            i for i, ln in enumerate(original) if "write_data\tHEA_init_edge1.data" in ln
        )
    except StopIteration:
        raise PipelineError("Template in.build_edge missing write_data HEA_init_edge1.data marker")

    left_block = original[: idx_write1 + 1]
    right_block = original[idx_write1 + 1 :]

    left_replaced = replace_common(left_block, side="left")
    right_replaced = replace_common(right_block, side="right")

    new_text = "\n".join(left_replaced + right_replaced) + "\n"
    output_path.write_text(new_text)


def run_cmd(cmd: List[str], cwd: Path, log_path: Path) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    with open(log_path, "a") as f:
        f.write("===== CMD =====\n")
        f.write(" ".join(cmd) + "\n")
        f.write(proc.stdout)
        f.write("\n")
    return proc


def run_cmd_stream(
    cmd: List[str], cwd: Path, log_path: Path, stage_stdout_path: Path
) -> int:
    """
    Stream process output line-by-line to both pipeline.log and a stage-specific
    STDOUT file so the user can inspect the original output easily.
    Returns the process return code.
    """
    # Ensure parent exists
    stage_stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as logf, open(stage_stdout_path, "w") as outf:
        logf.write("===== CMD (stream) =====\n")
        logf.write(" ".join(cmd) + "\n")
        logf.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        try:
            for line in proc.stdout:  # type: ignore
                logf.write(line)
                outf.write(line)
        finally:
            proc.wait()
    return proc.returncode


def run_lammps_build(run_dir: Path) -> None:
    log = run_dir / "pipeline.log"
    with open(log, "a") as f:
        f.write("\n=== BUILD START ===\n")
    cmd = [
        "mpirun",
        "-np",
        "1",
        str(LAMMPS_EXE),
        "-in",
        "in.build_edge",
    ]
    rc = run_cmd_stream(cmd, cwd=run_dir, log_path=log, stage_stdout_path=run_dir / "STDOUT.build")
    if rc != 0:
        raise PipelineError("LAMMPS build stage failed. See pipeline.log")
    with open(log, "a") as f:
        f.write("=== BUILD END (OK) ===\n")


def run_align(run_dir: Path, np: int) -> str:
    log = run_dir / "pipeline.log"
    np = cap_cores(np)
    with open(log, "a") as f:
        f.write("\n=== ALIGN START ===\n")
    cmd = [
        "mpirun",
        "-np",
        str(np),
        sys.executable,
        "align_mpi.py",
    ]
    rc = run_cmd_stream(cmd, cwd=run_dir, log_path=log, stage_stdout_path=run_dir / "STDOUT.align")
    with open(log, "a") as f:
        f.write("=== ALIGN END ===\n")
    # Read stage stdout to determine success/issue signature
    try:
        out_text = (run_dir / "STDOUT.align").read_text()
    except Exception:
        out_text = ""
    return out_text


def run_gen_aligned(run_dir: Path) -> None:
    log = run_dir / "pipeline.log"
    with open(log, "a") as f:
        f.write("\n=== GEN_ALIGNED START ===\n")
    cmd = [sys.executable, "gen_aligned_structure.py"]
    rc = run_cmd_stream(cmd, cwd=run_dir, log_path=log, stage_stdout_path=run_dir / "STDOUT.gen")
    if rc != 0:
        raise PipelineError("gen_aligned_structure.py failed. See pipeline.log")
    with open(log, "a") as f:
        f.write("=== GEN_ALIGNED END (OK) ===\n")


def run_minimize(run_dir: Path, np: int) -> None:
    log = run_dir / "pipeline.log"
    np = cap_cores(np)
    with open(log, "a") as f:
        f.write("\n=== MINIMIZE START ===\n")
    cmd = [
        "mpirun",
        "-np",
        str(np),
        str(LAMMPS_EXE),
        "-in",
        "in.min",
    ]
    rc = run_cmd_stream(cmd, cwd=run_dir, log_path=log, stage_stdout_path=run_dir / "STDOUT.min")
    if rc != 0:
        raise PipelineError("LAMMPS minimize stage failed. See pipeline.log")
    with open(log, "a") as f:
        f.write("=== MINIMIZE END (OK) ===\n")


def postprocess_final_cfg(run_dir: Path) -> Optional[Path]:
    cfg = run_dir / "final.cfg"
    if not cfg.exists():
        return None
    lines = cfg.read_text().splitlines()
    kept: List[str] = []
    for idx, ln in enumerate(lines, start=1):
        if idx in (1, 2, 3):
            continue
        if 5 <= idx <= 9:
            continue
        kept.append(ln)
    out = run_dir / "final.txt"
    out.write_text("\n".join(kept) + "\n")
    with open(run_dir / "pipeline.log", "a") as f:
        f.write("=== POSTPROCESS final.cfg -> final.txt (OK) ===\n")
    return out


def try_send_email(email: Optional[str], subject: str, body: str) -> None:
    if not email:
        return
    # Try 'mail' command if available
    mail_path = shutil.which("mail") or shutil.which("mailx")
    if mail_path:
        try:
            proc = subprocess.run(
                [mail_path, "-s", subject, email],
                input=body,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            # Log but don't raise
            return
        except Exception:
            pass
    # Fallback: write a notification file
    notif = REPO_ROOT / "email_notifications.log"
    with open(notif, "a") as f:
        f.write(f"TO: {email}\nSUBJECT: {subject}\n{body}\n---\n")


def sequence_offsets() -> List[int]:
    # +2, -2, +4, -4, +6, -6, ... up to a reasonable bound
    offsets: List[int] = []
    for step in range(1, 51):
        offsets.append(2 * step)
        offsets.append(-2 * step)
    return offsets


def format_lr_directory_name(x1: int, x2: int) -> str:
    """
    Format the L_R directory name correctly.
    This handles the existing naming convention used in the codebase.
    """
    return f"L{x1}_R{x2}"


def find_next_directory_number(base_dir: Path) -> int:
    """
    Find the next available next_ directory number.
    If no next_ directories exist, return 1.
    """
    next_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("next_")]
    if not next_dirs:
        return 1
    
    # Extract numbers from existing next_ directories
    numbers = []
    for d in next_dirs:
        try:
            num = int(d.name.split("_")[1])
            numbers.append(num)
        except (IndexError, ValueError):
            continue
    
    if not numbers:
        return 1
    
    return max(numbers) + 1


def create_next_directory(structure_dir: Path, ratio: str, x1: int, x2: int) -> Path:
    """
    Create a next_ directory and copy in.min and in.neb files.
    Returns the path to the created next directory.
    """
    # Find the base L_R directory
    ratio_dir = structure_dir / ratio
    lr_dir = ratio_dir / format_lr_directory_name(x1, x2)
    
    if not lr_dir.exists():
        raise PipelineError(f"Base directory {lr_dir} does not exist")
    
    # Find next directory number (look inside the L_R directory)
    next_num = find_next_directory_number(lr_dir)
    next_dir = lr_dir / f"next_{next_num}"
    next_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy in.min and in.neb files
    in_min_src = lr_dir / "in.min"
    in_neb_src = lr_dir / "in.neb"
    
    # At least one file must exist
    if not in_min_src.exists() and not in_neb_src.exists():
        raise PipelineError(f"Neither in.min nor in.neb found in {lr_dir}")
    
    # Copy files that exist
    if in_min_src.exists():
        in_min_dst = next_dir / "in.min"
        shutil.copy2(in_min_src, in_min_dst)
    
    if in_neb_src.exists():
        in_neb_dst = next_dir / "in.neb"
        shutil.copy2(in_neb_src, in_neb_dst)
    
    return next_dir, next_num


def modify_in_min_for_next(in_min_path: Path, next_num: int, l_value: int, r_value: int) -> None:
    """
    Modify the read_data paths in in.min file based on next number and specified L/R values.
    Since next_ directories are now inside L..._R... directories:
    - If next_num == 1: change to ../neb_{l_value}.data and ../neb_{r_value}.data
    - If next_num > 1: change to ../next_{next_num-1}/neb_{l_value}.data and ../next_{next_num-1}/neb_{r_value}.data
    """
    text = in_min_path.read_text()
    
    if next_num == 1:
        # For next_1, use ../neb_{l_value}.data and ../neb_{r_value}.data
        text = re.sub(
            r"^read_data\s+HEA_init_edge1\.data$",
            f"read_data       ../neb_{l_value}.data",
            text,
            flags=re.MULTILINE
        )
        text = re.sub(
            r"^read_data\s+HEA_init_edge3\.data$",
            f"read_data       ../neb_{r_value}.data",
            text,
            flags=re.MULTILINE
        )
    else:
        # For next_n where n > 1, use ../next_{n-1}/neb_{l_value}.data and ../next_{n-1}/neb_{r_value}.data
        prev_dir = f"../next_{next_num-1}"
        text = re.sub(
            r"^read_data\s+HEA_init_edge1\.data$",
            f"read_data       {prev_dir}/neb_{l_value}.data",
            text,
            flags=re.MULTILINE
        )
        text = re.sub(
            r"^read_data\s+HEA_init_edge3\.data$",
            f"read_data       {prev_dir}/neb_{r_value}.data",
            text,
            flags=re.MULTILINE
        )
    
    in_min_path.write_text(text)


def prepare_run_directory(
    structure_dir: Path, ratio: str, x1: int, x2: int
) -> Path:
    ratio_dir = structure_dir / ratio
    ratio_dir.mkdir(parents=True, exist_ok=True)
    run_dir = ratio_dir / format_lr_directory_name(x1, x2)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def prepare_inputs(run_dir: Path, structure_dir: Path, ratio: str, x1: int, x2: int) -> None:
    # 1) Prepare perfect_B2_adjusted.lmp
    source_b2 = find_perfect_b2_path(structure_dir)
    adjusted = run_dir / "perfect_B2_adjusted.lmp"
    comp = RATIO_TO_COMPOSITION[ratio]
    if comp is None:
        # Skip adjust: copy as-is to adjusted path for uniform downstream
        shutil.copy2(source_b2, adjusted)
    else:
        ti, zr, hf = comp
        cmd = [
            sys.executable,
            str(ADJUST_SPECIES_PY),
            "--input",
            str(source_b2),
            "--output",
            str(adjusted),
            "--ti_frac",
            str(ti),
            "--zr_frac",
            str(zr),
            "--hf_frac",
            str(hf),
        ]
        result = run_cmd(cmd, cwd=run_dir, log_path=run_dir / "pipeline.log")
        if result.returncode != 0 or (not adjusted.exists()):
            raise PipelineError(
                f"adjust_species.py failed for ratio {ratio}. See pipeline.log"
            )

    # 2) Generate in.build_edge customized
    generate_in_build_edge(REF_BUILD_EDGE, run_dir / "in.build_edge", x1=x1, x2=x2)

    # 3) Copy align/gen scripts (local copies for clarity)
    shutil.copy2(ALIGN_MPI_PY, run_dir / "align_mpi.py")
    shutil.copy2(GEN_ALIGNED_STRUCTURE_PY, run_dir / "gen_aligned_structure.py")

    # 4) Copy in.min with absolute SNAP paths
    copy_with_absolute_snap_paths(REF_IN_MIN, run_dir / "in.min")

    # 5) Copy in.neb template
    shutil.copy2(REF_IN_NEB, run_dir / "in.neb")

    # 6) Place absolute SNAP files if desired (not necessary; we reference absolute paths)
    # No copy needed to avoid duplication.


def execute_workflow(run_dir: Path, align_np: int) -> Tuple[bool, str]:
    # Build
    run_lammps_build(run_dir)
    # Align
    out = run_align(run_dir, align_np)
    if "ID comflict has Determined!" in out:
        return False, out
    if "NEB ID Alignment Completed!" not in out:
        # treat ambiguous output as failure
        return False, out
    # Generate aligned structure
    run_gen_aligned(run_dir)
    # Success up to gen_aligned
    return True, out


def run_with_retries(
    structure_dir: Path,
    ratio: str,
    base_x1: int,
    base_x2: int,
    align_np: int,
    email: Optional[str],
) -> Tuple[bool, Path, str]:
    # First attempt with base x1/x2
    attempts: List[Tuple[int, int]] = [(base_x1, base_x2)]
    for off in sequence_offsets():
        attempts.append((base_x1 + off, base_x2 + off))

    for idx, (x1_try, x2_try) in enumerate(attempts, start=1):
        run_dir = prepare_run_directory(structure_dir, ratio, x1_try, x2_try)
        status_txt = run_dir / "status.txt"
        try:
            prepare_inputs(run_dir, structure_dir, ratio, x1_try, x2_try)
            # Status breadcrumbs
            status_txt.write_text("BUILD prepared.\n")
            ok, align_out = execute_workflow(run_dir, align_np)
            if ok:
                msg = (
                    f"SUCCESS: {structure_dir.name}/{ratio}/L{x1_try}_R{x2_try} completed.\n"
                )
                status_txt.write_text(msg)
                return True, run_dir, msg
            else:
                msg = (
                    f"ALIGNMENT FAILURE (attempt {idx}): ID conflict for {structure_dir.name}/{ratio}/L{x1_try}_R{x2_try}.\n"
                )
                status_txt.write_text(msg + "\n" + align_out)
                # continue to next attempt
        except Exception as e:
            err_msg = (
                f"ERROR (attempt {idx}): {structure_dir.name}/{ratio}/L{x1_try}_R{x2_try}: {e}\n"
            )
            status_txt.write_text(err_msg)
            # continue to next attempt

    # All attempts exhausted
    return False, run_dir, "All retry attempts exhausted without success."


def main() -> None:
    ensure_paths()

    parser = argparse.ArgumentParser(description="Run NEB pipeline end-to-end")
    parser.add_argument("--slip", default=None, help="Slip system directory name (e.g., edge_b100_p100_NEB)")
    parser.add_argument("--structure", type=int, default=None, help="Structure index 1-5 or 0 for all structures")
    parser.add_argument("--x1", type=int, default=None, help="Left start index (int)")
    parser.add_argument("--x2", type=int, default=None, help="Right start index (int)")
    parser.add_argument("--align-np", type=int, default=DEFAULT_ALIGN_NP, help="MPI ranks for alignment (<=256)")
    # parser.add_argument("--min-np", type=int, default=DEFAULT_MIN_NP, help="MPI ranks for minimize (<=256)")
    parser.add_argument("--email", default=None, help="Email for notifications (optional)")
    parser.add_argument("--ratios", nargs="*", default=["12.5pct", "16.7pct", "20pct", "25pct"], help="Ratios to run")
    parser.add_argument("--jobs", type=int, default=None, help="Max parallel jobs (auto if unset)")
    parser.add_argument("--next", nargs=2, type=int, metavar=("L", "R"), help="Create next_ directory with modified in.min and in.neb files. Specify L and R values for read_data paths.")

    args = parser.parse_args()

    slip_system = prompt_if_none(args.slip, "Enter slip system (e.g., edge_b100_p100_NEB): ")
    structure_choice_str = prompt_if_none(
        None if args.structure is None else str(args.structure),
        "Enter structure (1-5, or 0 for all): ",
        choices=["0", "1", "2", "3", "4", "5"],
    )
    structure_choice = int(structure_choice_str)

    x1_str = prompt_if_none(None if args.x1 is None else str(args.x1), "Enter x1 (int): ")
    x2_str = prompt_if_none(None if args.x2 is None else str(args.x2), "Enter x2 (int): ")
    x1 = int(x1_str)
    x2 = int(x2_str)

    align_np = cap_cores(args.align_np)
    # min_np removed (no in.min stage)
    email = args.email or None

    cfg = RunConfig(
        slip_system=slip_system,
        structure_choice=structure_choice,
        x1=x1,
        x2=x2,
        align_np=align_np,
        min_np=align_np,  # Use align_np as min_np since min stage is removed
        email=email,
    )

    # Handle next_ functionality
    if args.next:
        # For next_ functionality, we only work with a single structure
        if structure_choice == 0:
            raise PipelineError("next_ functionality requires specifying a single structure (1-5), not 0 for all")
        
        # Extract L and R values from --next arguments
        next_l, next_r = args.next
        
        structure_dir = locate_structure_dir(cfg.slip_dir, cfg.structure_choice)
        
        # Process each ratio
        for ratio in args.ratios:
            if ratio not in RATIO_TO_COMPOSITION:
                raise PipelineError(f"Unknown ratio: {ratio}")
            
            try:
                next_dir, next_num = create_next_directory(structure_dir, ratio, cfg.x1, cfg.x2)
                
                # Modify in.min if it exists
                in_min_path = next_dir / "in.min"
                if in_min_path.exists():
                    modify_in_min_for_next(in_min_path, next_num, next_l, next_r)
                    print(f"Created next_{next_num} directory: {next_dir}")
                    print(f"Modified in.min with read_data paths: ../neb_{next_l}.data and ../neb_{next_r}.data")
                else:
                    print(f"Created next_{next_num} directory: {next_dir}")
                    print(f"Note: No in.min file found to modify")
                    
            except Exception as e:
                print(f"Error creating next_ directory for {ratio}: {e}")
        
        return  # Exit after handling next_ functionality

    # Build list of structure dirs
    structure_dirs: List[Path] = []
    if structure_choice == 0:
        # all structures 1..5
        for sid in range(1, 6):
            try:
                structure_dirs.append(locate_structure_dir(cfg.slip_dir, sid))
            except Exception:
                continue
    else:
        structure_dirs.append(locate_structure_dir(cfg.slip_dir, cfg.structure_choice))

    # Parallel scheduling across structures and ratios respecting core cap
    ratios = args.ratios
    for r in ratios:
        if r not in RATIO_TO_COMPOSITION:
            raise PipelineError(f"Unknown ratio: {r}")

    per_job_cores = cfg.align_np
    total_jobs = len(structure_dirs) * len(ratios)
    auto_jobs = max(1, min(total_jobs, MAX_TOTAL_CORES // per_job_cores))
    max_jobs = args.jobs if args.jobs is not None else auto_jobs
    if max_jobs <= 0:
        max_jobs = 1

    successes: List[Tuple[Path, str]] = []
    failures: List[str] = []
    with ThreadPoolExecutor(max_workers=max_jobs) as executor:
        futures = []
        for sdir in structure_dirs:
            for ratio in ratios:
                futures.append(
                    executor.submit(
                        run_with_retries,
                        sdir,
                        ratio,
                        cfg.x1,
                        cfg.x2,
                        cfg.align_np,
                        cfg.email,
                    )
                )
        for fut in as_completed(futures):
            ok, run_dir, msg = fut.result()
            if ok:
                successes.append((run_dir, msg))
            else:
                failures.append(msg)

    # After all gen_aligned_structure done, send summary email
    if cfg.email:
        subject = f"NEB pipeline summary: {cfg.slip_system} structures={'all' if structure_choice==0 else structure_choice}"
        lines: List[str] = []
        if successes:
            lines.append("SUCCESS runs:")
            for rd, msg in successes:
                lines.append(f"- {msg.strip()} @ {rd}")
        if failures:
            lines.append("FAILURE runs:")
            for m in failures:
                lines.append(f"- {m}")
        if not lines:
            lines.append("No runs executed.")
        try_send_email(cfg.email, subject=subject, body="\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user")
        sys.exit(130)
    except PipelineError as e:
        print(f"Pipeline error: {e}")
        sys.exit(2)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


