#!/bin/bash

received_var1=$1
received_var2=$2
received_var3=$3
received_var4=$4

lx=$(sed -n "6,6p" $received_var1.lmp | awk '{print $2}'| awk '{printf("%f",$0)}')
ly=$(sed -n "7,7p" $received_var1.lmp | awk '{print $2}'| awk '{printf("%f",$0)}')
lz=$(sed -n "8,8p" $received_var1.lmp | awk '{print $2}'| awk '{printf("%f",$0)}')
xc=$(echo $lx*0.55 |bc)
zc=$(echo $lz*0.55 |bc)
lb=$(echo $lx/$received_var4 | bc)


atomsk $received_var1.lmp -sub 1 Ni -sub 2 Co -sub 3 Ti -sub 4 Zr -dislocation $zc $xc edge_rm y z $lb 0.3 lmp

mv $received_var1.lmp ${received_var1}_init_edge.data
cp ${received_var1}_init_edge.data ../$received_var3/

