import os
import numpy as np
from operator import itemgetter
from ovito.io import import_file, export_file
from ovito.modifiers import DislocationAnalysisModifier
from ovito.data import DislocationNetwork


def get_dislocation(filename):
    pipeline = import_file(filename)
    modifier = DislocationAnalysisModifier()
    modifier.input_crystal_structure = DislocationAnalysisModifier.Lattice.BCC
    modifier.defect_mesh_smoothing_level = 20
    modifier.circuit_stretchability = 30
    modifier.line_point_separation = 1.0
    pipeline.modifiers.append(modifier)
    data = pipeline.compute()
    linepoints = []
    for segment in data.dislocations.segments:
        for i in range(len(segment.points)):
            linepoints.append([segment.points[i][0],segment.points[i][1],segment.points[i][2]])
    return linepoints

points = get_dislocation("neb_7.data")

with open("dislocation_points.txt", "w") as f:
    for p in points:
        f.write(f"{p[0]} {p[1]} {p[2]}\n")
