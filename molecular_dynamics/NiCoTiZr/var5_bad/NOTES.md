# Why this run is marked "bad"

Kept for reference, not because it produced a valid result. Compared to
the other `var*` setups in this folder (e.g. `var4/`), this one:

- reads structure from `../NiCoTiZr_lmp` instead of the standard
  `HEA_init.data` used elsewhere
- runs only 100,000 steps instead of 500,000

This combination (non-standard starting structure + short run) is the
likely reason it was flagged as a bad/aborted attempt rather than a
usable result. The original run output isn't in this repo (raw
simulation outputs are excluded — see the top-level README), so this is
inferred from the input script, not confirmed from a log.
