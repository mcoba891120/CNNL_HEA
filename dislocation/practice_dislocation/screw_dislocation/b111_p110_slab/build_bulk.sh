#!/bin/bash

mkdir -p MD_300K_relax
sed  "s/currtemp/300/g" in.relax_bulk > MD_300K_relax/in.relax_bulk

#mkdir -p MD_1273K_relax
#sed  "s/currtemp/1273/g" in.relax_bulk > MD_1273K_relax/in.relax_bulk
