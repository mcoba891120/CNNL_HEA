# Naming conventions used across this repo

These conventions were reverse-engineered from the file/folder names and
script contents themselves (there was no original naming spec) — treat
this as a best-effort map, not a guaranteed-accurate spec.

## `var{N}` — parameter/composition variant number

Refers to a specific SNAP potential fit / composition variant, e.g.
`var8` pairs with potential files `HEA_var8.snapcoeff` /
`HEA_var8.snapparam` (or `MEA_var8.*` for the 4-element alloys — see
below). The same `var{N}` number means "use potential fit N", consistent
across `relaxation/`, `compression/`, `tension/`, `monte_carlo/`, etc.

## `HEA_var{N}` vs `MEA_var{N}` potential naming

Both prefixes are used for what is functionally the same kind of SNAP
potential file, inconsistently, by different people/scripts:
`HEA` (high-entropy alloy) is generally used for the 5-element
NiCoTiZrHf system, `MEA` (medium-entropy alloy) for the 4-element
NiCoTiZr system — but this isn't applied consistently (see
`relaxation/templates/in.relax.var.NiCoTiZr_HEApotential`, which is a
NiCoTiZr template that was written to reference an `HEA_var*` file
instead of `MEA_var*`).

## `v3_trial{N}`, `v4_trial{N}`, `v2_var{N}` — workflow-version + attempt

Seen mainly under `dislocation/`. `v3`/`v4` is the *workflow/procedure*
version (a redesign of how the dislocation build+relax steps were
chained), and `trial{N}` is a sequential attempt number within that
workflow version — higher trial numbers are later attempts, not
independent parallel variants. A `_1`/`_new` suffix (e.g. `v4_trial8_1`,
`v4_trial4_new`) marks a redo/correction of that same trial.

## `HEA_v{V}_trial{N}` potential files (`potentials/`)

Same idea applied to potential fits: `V` tracks which workflow-version's
dislocation runs the fit was produced/used for, `trial{N}` the attempt
number. These are otherwise unrelated to the `var{N}` numbering above —
`HEA_v3_trial3.snapcoeff` and `HEA_var3.snapcoeff` are two different
fits that happen to both use the digit 3.

## Orientation/loading tags (`edge_b100_p110`, `screw_b111_p110`, ...)

`edge`/`screw` = dislocation character; `b{hkl}` = Burgers vector
direction; `p{hkl}` = slip plane normal. `100`/`110`/`111` elsewhere
(e.g. `NiCoTiZrHf_110`) is the crystal orientation of the simulation
cell's z-axis.

## Temperature/atom-count suffixes (`var8_69120_600k`, ...)

`{var}_{total_atom_count}_{temperature}k` — a session name encoding the
potential variant, the total atom count in the built structure, and the
run temperature in Kelvin. A trailing `_yielding` marks a run carried
past the elastic regime to find the yield point; `_scaled` marks a
structure file that was rescaled (see
`strain_stress/mc900k/reshape_scaledInput.sh`) before use.

## Known inconsistencies (not resolved, just flagged)

- `dislocation/practice_dislocation/` has its own local naming drift —
  see `dislocation/practice_dislocation/README.md`.
- A few `var{N}_bad` folders exist (e.g.
  `molecular_dynamics/NiCoTiZr/var3_bad`) — see that folder's own
  `NOTES.md` for what's known about why.
- `monte_carlo/dislocation_fix/v3_trail3_MC*k`,
  `.../v4_trail7_MC` — "trail" is a typo for "trial", left uncorrected
  on purpose: `monte_carlo/dislocation_fix_MC.sh` (the actual cluster job
  script for these runs) builds this exact misspelled path at runtime
  (`SESSION_PATH="dislocation_fix/v3_trail3_MC${TEMPERATURE}k"`), so
  renaming the folder here would desync it from the script that produced
  it, not fix anything.
