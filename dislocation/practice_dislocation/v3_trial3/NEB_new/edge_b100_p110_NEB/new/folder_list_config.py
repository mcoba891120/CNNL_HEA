#!/usr/bin/env python3
"""
Configuration file for folder paths to analyze.
Modify the FOLDER_PATHS list to include your desired folders.
"""

import os

# Base path for all folders
BASE_PATH = "dislocation/practice_dislocation/v3_trial3/NEB_new/edge_b100_p110_NEB/new"

# List of folder paths to analyze
# You can modify this list to include any folders you want to process
FOLDER_PATHS = [
    # Main folders
    os.path.join(BASE_PATH, "change_ratio_12_5_300K"),
    os.path.join(BASE_PATH, "change_ratio_20_300K"),
    os.path.join(BASE_PATH, "change_ratio_25_300K"),
    
    # Subfolders
    os.path.join(BASE_PATH, "change_ratio_12_5_300K", "next1"),
    os.path.join(BASE_PATH, "change_ratio_12_5_300K", "from-13to1"),
    os.path.join(BASE_PATH, "change_ratio_12_5_300K", "from-1to13"),
    
    # Add more folders as needed
    # os.path.join(BASE_PATH, "your_folder_name"),
    # os.path.join(BASE_PATH, "another_folder"),
]

# Alternative: Define folders by pattern matching
# This will automatically find all folders matching certain patterns
AUTO_DISCOVER_PATTERNS = [
    "change_ratio_*_300K",  # All change_ratio folders
    "next*",                # All next folders
    "from-*to*",           # All from-XtoY folders
]

# Maximum screen number to look for (0 to MAX_SCREEN)
MAX_SCREEN = 8

# Output folder name
OUTPUT_FOLDER_NAME = "energy_analysis_results"

# Plot settings
PLOT_SETTINGS = {
    'figure_size': (14, 8),
    'dpi': 300,
    'marker_size': 8,
    'line_width': 2,
    'grid_alpha': 0.3,
}

# Colors for different folders (will cycle through these)
PLOT_COLORS = [
    '#1f77b4',  # blue
    '#ff7f0e',  # orange
    '#2ca02c',  # green
    '#d62728',  # red
    '#9467bd',  # purple
    '#8c564b',  # brown
    '#e377c2',  # pink
    '#7f7f7f',  # gray
    '#bcbd22',  # olive
    '#17becf',  # cyan
]
