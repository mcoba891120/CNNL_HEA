# CNNL_HEA

LAMMPS-based molecular dynamics / Monte Carlo simulation workflow for
studying high-entropy alloys (HEA) in the Ni-Co-Ti-Zr(-Hf) system:
dislocation behavior (edge/screw, NEB migration barriers), mechanical
response (compression, tension, stress-strain), and phase/composition
stability (Monte Carlo atom-swap equilibration).

This repo holds the **source and setup** side of that work — LAMMPS
input templates, structure-generation scripts, potential files, and
analysis notebooks — organized by what each piece *does*, not by which
cluster account or machine it originally lived on. Raw simulation
outputs (dump/data/restart files, structure files, logs, rendered
images/videos) are intentionally not included; see "What's not here"
below.

## Prerequisites

- **LAMMPS**, built with the SNAP and EAM pair styles (compositions
  here use SNAP potentials; the Fe reference cases use EAM/alloy).
- **[Atomsk](https://atomsk.univ-lille.fr/)** — used to generate initial
  structures (dislocation cuts, orientation builds).
- **Python 3** with `ase`, `numpy` — used by `HEA_gen.py` (and variants)
  to generate multi-element structure files from a template POSCAR/VASP
  structure.
- **MPI** (OpenMPI/MPICH) — LAMMPS runs here use `mpirun`/`mpiexec`.
- **OVITO** (`ovito` Python module) — used by the `analysis_and_plotting/ovito/`
  scripts for structure/strain analysis.
- A SLURM-based or interactive multi-GPU cluster if you want to
  reproduce the original scale of these runs — several driver scripts
  branch on `hostname` to pick the right LAMMPS binary/GPU. You don't
  need this to read or adapt the LAMMPS input decks themselves.

## Layout

| Folder | What's in it |
|---|---|
| `setup_and_automation/` | Structure-setup drivers (`auto_simulation.sh`, `HEA_gen.py`) and mode-specific job launchers under `drivers/`. **Start here** — see `setup_and_automation/README.md`. |
| `potentials/` | SNAP (`.snapcoeff`/`.snapparam`) and EAM (`.eam.alloy`) potential files. |
| `relaxation/` | Structure relaxation (`in.relax.*`) setups, incl. `heat_treatment/` and per-composition parameter sweeps. |
| `compression/` | Compression test (`in.compress.*`) setups per alloy/orientation. |
| `tension/` | Tension test (`in.tension.*`) setups. |
| `dislocation/` | Edge/screw dislocation construction and subsequent MD, incl. `stress_strain_extraction/` and early practice builds. |
| `neb/` | Nudged Elastic Band setups for dislocation migration barriers, plus a (currently broken-ish, see below) automation pipeline. |
| `monte_carlo/` | MC atom-swap/composition equilibration setups. |
| `molecular_dynamics/` | General MD relaxation/thermal runs. |
| `strain_stress/` | Stress-strain extraction workflow (structure reshape + MC-based sampling). |
| `analysis_and_plotting/` | Post-processing: plotting notebooks, OVITO-based structural analysis, Warren-Cowley short-range-order, neighbor/CRSS analysis. |
| `coursework_practice/` | Early coursework-style exercises — not part of the research workflow, kept separate. |

`NAMING.md` explains the naming conventions you'll run into everywhere
(`var{N}`, `v3_trial{N}`/`v4_trial{N}`, `HEA_var*` vs `MEA_var*`,
`edge_b100_p110`-style orientation tags, temperature/atom-count session
names). Read it before trying to guess what a folder name means.

## Typical workflow

The simulation stages generally chain in this order, matching the
folder layout above:

```
generate structure (Atomsk + HEA_gen.py)
        │
        ▼
   relaxation/  ──────────────┐
        │                     │
        ▼                     ▼
compression/ or tension/   monte_carlo/  (composition equilibration)
        │                     │
        ▼                     ▼
  strain_stress/         dislocation/ ──► neb/  (migration barriers)
        │                     │
        └──────────┬──────────┘
                    ▼
         analysis_and_plotting/
```

A structure is relaxed first; from there it either goes straight into a
mechanical test (compression/tension), gets Monte-Carlo–equilibrated to
a target composition/temperature before testing, or gets a dislocation
introduced (`dislocation/`) and optionally run through NEB to get a
migration energy barrier. Everything downstream funnels into
`analysis_and_plotting/` for post-processing.

## Running a simulation

Most setups follow the same interactive pattern, driven by
`setup_and_automation/auto_simulation.sh`:

```sh
cd setup_and_automation/
./auto_simulation.sh
# prompts for: simulation mode (relax/heat/compress/tension),
# alloy, orientation, session name, duplication factors,
# potential (PE) number, cores, run count, temperature
```

It generates the structure (via Atomsk + `HEA_gen.py`), builds the
LAMMPS input from the matching template in `relaxation/templates/`,
`compression/templates/`, or `tension/templates/` (substituting
`{{var_num}}`, `{{temperature}}`, etc.), and submits the job. See
`setup_and_automation/README.md` for the full parameter list, the
directory structure it creates, and which of the several
similarly-named scripts in that folder to use for which case (they are
*not* interchangeable copies — read that file before picking one).

For dislocation/NEB work specifically, look at the README/guide files
inside `dislocation/` and `neb/` directly — those stages have their own
multi-step pipelines (build → relax → introduce dislocation → NEB) that
don't go through `auto_simulation.sh`.

For post-processing, `analysis_and_plotting/` has notebooks organized
by analysis type (`plot/` for stress-strain and Young's-modulus curves,
`ovito/` for OVITO-based structural analysis, `short_range_order/` for
Warren-Cowley parameters). Most of them read output files this repo
doesn't include (see below) — you'll need to point them at your own run
directory's output.

## What's not here

- Simulation **outputs**: `.data`/`.cfg`/`.lmp`/`.dump`/`.pos`/`POSCAR`
  files, logs, rendered images/videos. These are regenerated by running
  the workflow above, not checked in.
- Third-party code: the LAMMPS source tree itself and the Atomsk
  binary/tarball.
- A handful of duplicate/junk files (editor autosaves, one corrupt
  archive) that were cleaned out.

