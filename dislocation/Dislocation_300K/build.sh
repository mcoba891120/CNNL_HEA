#!/bin/bash
lx=$(sed -n "6,6p" NiCoTiZrHf_46080.lmp | awk '{print $2}'| awk '{printf("%f",$0)}')
ly=$(sed -n "7,7p" NiCoTiZrHf_46080.lmp | awk '{print $2}'| awk '{printf("%f",$0)}')
lz=$(sed -n "8,8p" NiCoTiZrHf_46080.lmp | awk '{print $2}'| awk '{printf("%f",$0)}')
xc=$(echo $lx*0.5 |bc)
zc=$(echo $lz*0.5 |bc)
lb=$(echo $ly/10 | bc)

atomsk NiCoTiZrHf_46080.lmp -sub 1 Ni -sub 2 Co -sub 3 Ti -sub 4 Zr -sub 5 Hf -dislocation $zc $xc edge_rm y z $lb 0.0 lmp

mv NiCoTiZrHf_46080.lmp HEA_init_edge.data
