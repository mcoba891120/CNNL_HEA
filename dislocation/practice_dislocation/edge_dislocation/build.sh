#!/bin/bash
lx=$(sed -n "5,5p" HEA_init_B2.data | awk '{print $2}'| awk '{printf("%f",$0)}')
ly=$(sed -n "6,6p" HEA_init_B2.data | awk '{print $2}'| awk '{printf("%f",$0)}')
lz=$(sed -n "7,7p" HEA_init_B2.data | awk '{print $2}'| awk '{printf("%f",$0)}')
xc=$(echo $lx*0.5 |bc)
zc=$(echo $lz*0.5 |bc)
lb=$(echo $ly/10 | bc)

~/atomsk_b0.12.1_Linux-amd64/atomsk HEA_init_B2.data -sub 1 Ni -sub 2 Co -sub 3 Ti -sub 4 Zr -dislocation $zc $xc edge_rm y z $lb 0.0 lmp

mv HEA_init_B2.lmp HEA_init_edge.data
