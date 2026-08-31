# practice_dislocation

This tree is exploratory/iterative dislocation-construction work, kept
separate from the final `dislocation/dislocation_fix/` and
`dislocation/Dislocation_*K/` results. Nothing under here should be
treated as a validated final result.

## Naming pattern

- `v3_trial{N}/`, `v4_trial{N}/` — successive attempts at the dislocation
  build/relax procedure within workflow version 3 or 4; higher trial
  numbers are later (usually better) attempts, not parallel variants.
  `v4_trial8_1`, `v4_trial9_1`, `v4_trial4_new` are re-runs/corrections of
  the same-numbered trial.
- `var{N}/` — parameter/composition variant number, see the repo-wide
  naming note in `../../NAMING.md`.
- `edge_dislocation/`, `screw_dislocation/`, `Fe_dislocation/`,
  `perfect_HEA/` — reference/baseline builds used to compare against.

## `v3_trial3/NEB_new/*/` sub-folders

Inside each orientation's `*_NEB/` folder there are further ad-hoc names
(`test/`, `new/`, `new_1/`, `thick/test_2/`, etc.) from iterating on the
NEB image/path setup by hand. These were **not** cleaned up or
individually documented by the original run — they're kept as-is because
splitting "which one worked" from "which one was a dead end" isn't
recoverable without the run logs, which are outside this repo's scope
(see the top-level README's "What's not here"). Treat everything under
`NEB_new/` as scratch/iteration history, not curated results.
