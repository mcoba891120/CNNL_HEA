#!/usr/bin/env python3
import argparse
import random
from typing import List, Tuple, Dict


SECTION_HEADERS = {
    "Masses",
    "Pair Coeffs",
    "PairIJ Coeffs",
    "Atoms",
    "Velocities",
    "Bonds",
    "Angles",
    "Dihedrals",
    "Impropers",
    "Ellipsoids",
    "Lines",
    "Triangles",
    "Bodies",
}


def find_section(lines: List[str], header_name: str) -> Tuple[int, int]:
    """
    Find the start (first data line) and end (exclusive) indices of a section in a LAMMPS data file.

    Returns (start_idx, end_idx). If not found, returns (-1, -1).
    """
    header_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Match 'Atoms' or 'Atoms # atomic' etc.
        if stripped.startswith(header_name):
            # Ensure it's actually a header line (no leading digits)
            if not stripped[0].isdigit():
                header_idx = i
                break
    if header_idx == -1:
        return -1, -1

    # The data typically starts after one blank line following the header
    start_idx = header_idx + 1
    while start_idx < len(lines) and not lines[start_idx].strip():
        start_idx += 1

    # Find end: next header or EOF
    end_idx = len(lines)
    for j in range(start_idx, len(lines)):
        stripped = lines[j].strip()
        if not stripped:
            continue
        # Detect a new section header (starts with a letter and matches known headers)
        if not stripped[0].isdigit():
            # A line like 'Velocities' or 'Bonds' etc.
            base = stripped.split()[0]
            if base in SECTION_HEADERS and base != header_name:
                end_idx = j
                break
    return start_idx, end_idx


def parse_atom_type_token_index(header_line: str) -> int:
    """
    For 'Atoms' section with style '# atomic', atom type is token index 1 (0-based) in typical formats.
    We keep this function for future extensibility; for now we assume index 1.
    """
    return 1


def adjust_types_randomly(
    atom_lines: List[int],
    lines: List[str],
    type_token_index: int,
    target_counts: Dict[int, int],
    controlled_types: List[int],
    rng: random.Random,
) -> None:
    """
    Adjust the atom types in-place in 'lines' for the rows listed in 'atom_lines',
    so that the counts of types in 'target_counts' are achieved. Only types listed
    in controlled_types are managed; donors may be drawn from any type if needed.
    """
    # Collect current types and indices by type
    indices_by_type: Dict[int, List[int]] = {}
    other_indices: List[int] = []

    for idx in atom_lines:
        raw = lines[idx].split("#", 1)[0].strip()
        if not raw:
            continue
        tokens = raw.split()
        try:
            t = int(tokens[type_token_index])
        except (IndexError, ValueError):
            continue
        indices_by_type.setdefault(t, []).append(idx)

    # Build list of all atom indices in Atoms section
    all_atom_indices = [idx for idx in atom_lines if lines[idx].strip() and lines[idx].strip()[0].isdigit()]

    # Prepare pools and deficits
    deficits: Dict[int, int] = {}
    donors_pool: List[int] = []

    for t, desired in target_counts.items():
        current = len(indices_by_type.get(t, []))
        delta = desired - current
        deficits[t] = delta
        if delta < 0:
            # Excess: pick |delta| donors from this type
            pool = indices_by_type.get(t, [])[:]
            rng.shuffle(pool)
            donors_pool.extend(pool[: -delta])

    # If we still need more donors, draw from other types
    needed = sum(v for v in deficits.values() if v > 0)
    if len(donors_pool) < needed:
        # Build pool of non-controlled or controlled-without-excess indices
        controlled = set(controlled_types)
        used = set(donors_pool)
        for idx in all_atom_indices:
            if idx in used:
                continue
            raw = lines[idx].split("#", 1)[0].strip()
            if not raw:
                continue
            tokens = raw.split()
            try:
                t = int(tokens[type_token_index])
            except (IndexError, ValueError):
                continue
            # Accept donors if type not in controlled, or in controlled but not currently in deficit
            if t not in controlled or deficits.get(t, 0) <= 0:
                other_indices.append(idx)
        rng.shuffle(other_indices)
        donors_pool.extend(other_indices[: max(0, needed - len(donors_pool))])

    if len(donors_pool) < needed:
        raise RuntimeError("Not enough donor atoms to satisfy requested target counts.")

    rng.shuffle(donors_pool)

    # Assign donors to deficit types
    take_ptr = 0
    for t, delta in deficits.items():
        if delta <= 0:
            continue
        for _ in range(delta):
            idx = donors_pool[take_ptr]
            take_ptr += 1
            # Replace type token on this line
            # Preserve inline comments
            line = lines[idx]
            before, after_comment = (line.split('#', 1) + [""])[:2]
            tokens = before.strip().split()
            if len(tokens) <= type_token_index:
                continue
            tokens[type_token_index] = str(t)
            new_before = " ".join(tokens)
            if after_comment:
                lines[idx] = f"{new_before} #" + after_comment
            else:
                lines[idx] = new_before + "\n"


def main():
    parser = argparse.ArgumentParser(description="Adjust Ti/Zr/Hf composition in a LAMMPS data file with randomness.")
    parser.add_argument("--input", default="perfect_B2.lmp", help="Path to input LAMMPS data file")
    parser.add_argument("--output", default="perfect_B2_adjusted.lmp", help="Path to output LAMMPS data file")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--ti_type", type=int, default=3, help="Atom type ID for Ti")
    parser.add_argument("--zr_type", type=int, default=4, help="Atom type ID for Zr")
    parser.add_argument("--hf_type", type=int, default=5, help="Atom type ID for Hf")
    parser.add_argument("--ti_frac", type=float, default=0.125, help="Target overall fraction for Ti")
    parser.add_argument("--zr_frac", type=float, default=0.25, help="Target overall fraction for Zr")
    parser.add_argument("--hf_frac", type=float, default=0.125, help="Target overall fraction for Hf")

    args = parser.parse_args()

    rng = random.Random(args.seed)

    with open(args.input, "r") as f:
        lines = f.readlines()

    # Locate Atoms section
    atoms_start, atoms_end = find_section(lines, "Atoms")
    if atoms_start == -1:
        raise RuntimeError("Could not find 'Atoms' section in the input file.")

    # Determine type token index (assume atomic style)
    type_token_index = parse_atom_type_token_index(lines[atoms_start - 1] if atoms_start - 1 >= 0 else "")

    # Collect atom line indices within Atoms section
    atom_line_indices: List[int] = []
    for i in range(atoms_start, atoms_end):
        stripped = lines[i].strip()
        if not stripped or not stripped[0].isdigit():
            continue
        atom_line_indices.append(i)

    total_atoms = len(atom_line_indices)
    if total_atoms == 0:
        raise RuntimeError("No atom lines found in 'Atoms' section.")

    # Targets (overall fractions of total atoms)
    targets = {
        int(args.ti_type): int(round(args.ti_frac * total_atoms)),
        int(args.zr_type): int(round(args.zr_frac * total_atoms)),
        int(args.hf_type): int(round(args.hf_frac * total_atoms)),
    }

    # Ensure we don't demand more than total; if rounding overflow, trim Zr then Ti then Hf in that order
    overflow = sum(targets.values()) - total_atoms
    if overflow > 0:
        for key in [int(args.zr_type), int(args.ti_type), int(args.hf_type)]:
            if overflow <= 0:
                break
            take = min(overflow, targets[key])
            targets[key] -= take
            overflow -= take

    adjust_types_randomly(
        atom_lines=atom_line_indices,
        lines=lines,
        type_token_index=type_token_index,
        target_counts=targets,
        controlled_types=[int(args.ti_type), int(args.zr_type), int(args.hf_type)],
        rng=rng,
    )

    with open(args.output, "w") as f:
        f.writelines(lines)

    print(
        f"Wrote adjusted file to {args.output} with targets: "
        f"Ti({args.ti_type})={targets[int(args.ti_type)]}, "
        f"Zr({args.zr_type})={targets[int(args.zr_type)]}, "
        f"Hf({args.hf_type})={targets[int(args.hf_type)]}"
    )


if __name__ == "__main__":
    main()


