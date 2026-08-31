#!/bin/bash

mkdir -p MD_300K_new_relax
sed  "s/currtemp/300/g" in.relax_bulk > MD_300K_new_relax/in.relax_bulk

#mkdir -p MD_600K_relax
#sed  "s/currtemp/600/g" in.relax_bulk > MD_600K_relax/in.relax_bulk

#mkdir -p MD_900K_relax
#sed  "s/currtemp/900/g" in.relax_bulk > MD_900K_relax/in.relax_bulk

mkdir -p MD_1273K_new_relax
sed  "s/currtemp/1273/g" in.relax_bulk > MD_1273K_new_relax/in.relax_bulk

