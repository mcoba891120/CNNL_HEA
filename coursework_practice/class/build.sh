#!/bin/bash
lx=$(sed -n "6,6p" 111_test.lmp | awk '{print $2}'| awk '{printf("%f",$0)}')
ly=$(sed -n "7,7p" 111_test.lmp | awk '{print $2}'| awk '{printf("%f",$0)}')
lz=$(sed -n "8,8p" 111_test.lmp | awk '{print $2}'| awk '{printf("%f",$0)}')
xc=$(echo $lx*0.51 | bc)
zc=$(echo $lz*0.51+0.6 | bc)
lb=$(echo $lx/28 | bc)

atomsk 111_test.lmp -sub 1 Ni -sub 2 Co -sub 3 Ti -sub 4 Zr -dislocation $zc $xc edge_rm y z $lb 0.3 lmp

mv 111_test.lmp 111_test_edge.data

