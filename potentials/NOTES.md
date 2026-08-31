# On the remaining broken `pair_coeff` references

As of the last check, 95 `pair_coeff` potential-file tokens across `in.*`
files don't resolve to anything (down from an original 876, after a
multi-pass consolidation into this `potentials/` folder). Every one of
these was individually investigated; none is a leftover reorganization
artifact. They fall into three real categories:

## 1. `HEA.snapcoeff` / `HEA.snapparam` (14 refs) — not actually broken

`monte_carlo/templates/in.swap.HEA`, `molecular_dynamics/04_MC_300K/in.relax.HEA`,
and the five `dislocation/dislocation_fix/v4_trial7_MC/*/in.swap.HEA`
files all reference `../HEA.snapcoeff` / `../HEA.snapparam` — a bare
name with no version number. This is a **deliberate convention, not an
omission**: it expects whoever runs the script to have already copied
their chosen potential (renamed to exactly `HEA.snapcoeff`/`HEA.snapparam`)
into the parent directory first. It shows up in general-purpose
templates as well as the `v4_trial7_MC` runs, which rules out "someone
forgot to fill in a version number for this one experiment" — it's used
the same way everywhere. Nothing to fix here; a reader just needs to
know the convention.

## 2. One coeff/param mismatch that needs a human decision, not a guess

`dislocation/dislocation_fix/v3_trial3/screw_b111_p110/in.relax_slab_manual`
(note the filename — a manually-edited one-off, not a template output)
has:

```
pair_coeff * * potentials/HEA_v43_trial3.snapcoeff ../../../../potentials/HEA_v3_trial3.snapparam
```

`HEA_v43_trial3` looks like a typo for `HEA_v4_trial3` — but the
`.snapparam` on the same line points at `HEA_v3_trial3`, a *different*
trial. So this isn't a single-character fix: the coeff and param were
already mismatched (v4-ish vs. v3) before the typo. Since this repo's
policy throughout has been "don't guess at which potential a reference
meant — silently picking the wrong one is worse than an honest break",
this one was deliberately left alone rather than "fixed" toward an
assumption. If someone who remembers what this
run actually used sees this, it just needs one of the two trial numbers
picked to match the other.

## 3. Content that was never generated, verified against the live cluster

These reference potential fits/pairs that don't exist anywhere in this
repo. On 2026-08-31, with the original cluster still reachable, these
exact names were searched for directly on
`/work/cnnltmp01/mcoba891120`, `/work/cnnltmp01/ianiank2a`, and
`/work/jhenyu/hsieh` — **none of them exist there either.** This isn't
a gap introduced by this repo's construction; the fits were never
produced, or the run that would have produced them was never saved.

- `HEA_v7_trial6.snapcoeff`/`.snapparam` (60 refs, `dislocation/`) —
  `potentials/` has `HEA_v7_trial1` through `trial5`; trial6 was
  simply never completed/saved.
- `HEA_v5_trial8.snapcoeff`/`.snapparam` (12 refs, `relaxation/`) —
  same pattern; `trial1`–`trial7` exist, `trial8` doesn't.
- `HEA_v4_trial3.snapparam` (6 refs, `compression/`) — the matching
  `.snapcoeff` exists (`potentials/HEA_v4_trial3.snapcoeff`), but a
  `.snapparam` for it was never saved, so the pair is permanently
  incomplete.
- `MEA_var10.snapcoeff`/`.snapparam` (2 refs, `relaxation/`) —
  `var9` and `var11` exist; `var10` doesn't.

None of these can be recovered by rewriting a path — there's nothing to
point them at. Re-fitting them would mean re-running the SNAP training
pipeline from DFT data, which is out of scope for a repo reorganization
and would need to be done by whoever has the original DFT training set.
