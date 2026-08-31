#!/bin/bash

# Read-only scanner: list tasks that would be considered "ready for execution"
# according to neb_scheduler.sh logic, without copying files or launching jobs.

set -euo pipefail

NEB_ROOT="dislocation/practice_dislocation/v3_trial3/NEB_new"
SLIP_SYSTEMS=("edge_b100_p100_NEB" "edge_b100_p110_NEB" "edge_b110_p110_NEB" "edge_b111_p110_NEB" "screw_b100_p100_NEB" "screw_b100_p110_NEB" "screw_b110_p110_NEB" "screw_b111_p110_NEB")
STRUCTURES=("structure1" "structure2")
RATIOS=("12.5pct" "16.7pct" "20pct" "25pct")

is_running_dir() {
    local task_dir="$1"
    # Check if any mpirun process has this directory as CWD
    # (matches how jobs are launched: cd "$task_dir" && mpirun ...)
    local pid
    for pid in $(pgrep -f "mpirun" || true); do
        local cwd
        cwd=$(readlink "/proc/${pid}/cwd" 2>/dev/null || true)
        if [[ "$cwd" == "$task_dir" ]]; then
            return 0
        fi
    done
    return 1
}

is_completed_neb() {
    local task_dir="$1"
    # Consider NEB completed if any screen.* contains "Total wall time:"
    # Safe even if no files exist
    if find "$task_dir" -maxdepth 1 -name "screen.*" -type f -print -quit | grep -q .; then
        if grep -q "Total wall time:" "$task_dir"/screen.* 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

is_ready_dir() {
    local task_dir="$1"
    # Match neb_scheduler.sh:is_neb_ready but read-only:
    # 1) final.cfg must exist (in.min completed)
    # 2) Not completed (no "Total wall time:" in screen.*)
    # 3) Not currently running
    [[ -f "$task_dir/final.cfg" ]] || return 1
    if is_completed_neb "$task_dir"; then
        return 1
    fi
    if is_running_dir "$task_dir"; then
        return 1
    fi
    return 0
}

lr_ready=()
next_ready=()

for slip in "${SLIP_SYSTEMS[@]}"; do
  slip_dir="$NEB_ROOT/$slip"
  [[ -d "$slip_dir" ]] || continue
  for struct in "${STRUCTURES[@]}"; do
    struct_dir="$slip_dir/$struct"
    [[ -d "$struct_dir" ]] || continue
    for ratio in "${RATIOS[@]}"; do
      ratio_dir="$struct_dir/$ratio"
      [[ -d "$ratio_dir" ]] || continue
      # L*_R* directories
      for lr_dir in "$ratio_dir"/L*_R*; do
        [[ -d "$lr_dir" ]] || continue
        if is_ready_dir "$lr_dir"; then
          lr_ready+=("$lr_dir")
        fi
        # next_* under each L*_R*
        for next_dir in "$lr_dir"/next_*; do
          [[ -d "$next_dir" ]] || continue
          if is_ready_dir "$next_dir"; then
            next_ready+=("$next_dir")
          fi
        done
      done
    done
  done
done

echo "Found ${#lr_ready[@]} L*_R* tasks, ${#next_ready[@]} next_* tasks ready for execution"
if (( ${#lr_ready[@]} > 0 )); then
  echo "=== L*_R* ready ==="
  printf "%s\n" "${lr_ready[@]}"
fi
if (( ${#next_ready[@]} > 0 )); then
  echo "=== next_* ready ==="
  printf "%s\n" "${next_ready[@]}"
fi




