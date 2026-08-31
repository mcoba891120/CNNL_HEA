#!/bin/bash
for d in step_*; do
  if [ -d "$d" ]; then
    (
      cd "$d" || exit
      for f in $(ls -v screen.* 2>/dev/null); do
        awk '/Energy initial, next-to-last, final =/{getline; v=$NF} END{if (v != "") print v}' "$f"
      done > NEB_energy.txt
    )
    echo "✔ Processed $d/NEB_energy.txt"
  fi
done
