#!/bin/bash

read -p "Enter the orientation (100, 111): " ORIENTATION
X=10
Y=10
Z=10

if [ "$ORIENTATION" -eq 100 ]; then
    TOTAL_ATOM=$((X*Y*Z*2))
    ORIENTATION_STRING="[100] [010] [001]"
elif [ "$ORIENTATION" -eq 111 ]; then
    TOTAL_ATOM=$((X*Y*Z*12))
    ORIENTATION_STRING="[111] [1-10] [11-2]"
else
    echo "Invalid orientation"
    exit 1
fi

echo "y" | atomsk --create CsCl 3.0 Ni Ti orient $ORIENTATION_STRING -duplicate $X $Y $Z pos

echo "Total atoms: $TOTAL_ATOM"