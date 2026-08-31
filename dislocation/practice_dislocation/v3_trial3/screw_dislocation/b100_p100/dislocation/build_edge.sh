#!/bin/bash

perfect_B2="$1"
y_duplication="$2"

# 用 sed 一次替換所有大括號佔位符
sed -e "s|{perfect_B2}|${perfect_B2}|g" \
    -e "s|{y_duplication}|${y_duplication}|g" \
    in.build_edge > in.build_edge

# 呼叫 LAMMPS 讀取替換後的檔案
/home/jhenyu/lammps-stable_2Aug2023_update2/src/lmp_g++_openmpi -in in.build_edge

