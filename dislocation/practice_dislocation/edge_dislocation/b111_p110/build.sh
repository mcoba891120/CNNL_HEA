#!/bin/bash
lx=$(sed -n "5,5p" POSCAR_modified.data | awk '{print $2}'| awk '{printf("%f",$0)}')
ly=$(sed -n "6,6p" POSCAR_modified.data | awk '{print $2}'| awk '{printf("%f",$0)}')
lz=$(sed -n "7,7p" POSCAR_modified.data | awk '{print $2}'| awk '{printf("%f",$0)}')
xc=$(echo $lx*0.5-1.0 |bc)
zc=$(echo $lz*0.5-1.5 |bc)
lb=$(echo $lx/28 | bc)

/work/jhenyu/hsieh/atomsk_b0.13.1_Linux-amd64/atomsk POSCAR_modified.data -sub 1 Ni -sub 2 Co -sub 3 Ti -sub 4 Zr -sub 5 Hf -dislocation $zc $xc edge y z $lb 0.50 lmp

mv POSCAR_modified.lmp HEA_init_edge.data
