#!/bin/bash

# Create a series of folders fo v3_trial3_9792 under different temperature and slip system and finally put the corresponding SS_curve files into the folder

for temperatue in "300k" "600k" "900k" ; do
    for slip_system in "b100p110" "b111p110" ;do
        # Create the folder
        folder_name="v3_trial3_9792_${temperatue}_${slip_system}"
        mkdir -p "$folder_name"

        # Move the SS_curve files into the folder
        mv "SS_curve_v3_trial3_${temperatue}_${slip_system}.txt" "$folder_name/SS_curve_${temperatue}_${slip_system}.txt"
    done
done