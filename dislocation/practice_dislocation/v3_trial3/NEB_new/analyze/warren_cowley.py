import os
import numpy as np
import ase.io
from ase.io.lammpsdata import read_lammps_data
import math
from operator import itemgetter
from ovito.io import import_file, export_file
from ovito.modifiers import DislocationAnalysisModifier
from ovito.data import DislocationNetwork
import WarrenCowleyParameters as wc

def get_dislocation(filename):
    pipeline = import_file(filename)
    modifier = DislocationAnalysisModifier()
    modifier.input_crystal_structure = DislocationAnalysisModifier.Lattice.BCC
    modifier.defect_mesh_smoothing_level = 10
    modifier.trial_circuit_length = 30
    modifier.circuit_stretchability = 10
    modifier.line_point_separation = 0.5
    pipeline.modifiers.append(modifier)
    data = pipeline.compute()
    linepoints = []
    for segment in data.dislocations.segments:
        for i in range(len(segment.points)):
            linepoints.append([segment.points[i][0],segment.points[i][1],segment.points[i][2]])

    linepoints = np.array(linepoints)
    list_x = linepoints[:,0]
    max_x = np.max(list_x)
    min_x = np.min(list_x)
    max_id = np.argmax(list_x)
    min_id = np.argmin(list_x)
    ### find the first fastest and slowest linepoints ###
    fast_pid = []
    slow_pid = []
    for i in range(3):
        fid = max_id-i-1
        if fid < 0:
            fid = len(linepoints)+fid
        elif fid > len(linepoints)-1:
            fid = fid-len(linepoints)
        fast_pid.append(fid)
        sid = min_id-i-1
        if sid < 0:
            sid = len(linepoints)+sid
        elif sid > len(linepoints)-1:
            sid = sid-len(linepoints)
        slow_pid.append(sid)
    return linepoints, fast_pid, slow_pid
    #########################################################
def get_dist(atom_pos,line_pos,cell):
    lenx = cell[0]
    leny = cell[1]
    lenz = cell[2]
    dispx = atom_pos[0]-line_pos[0]
    if dispx > 0.5*lenx: dispx -= lenx
    if dispx < -0.5*lenx: dispx += lenx
    dispy = atom_pos[1]-line_pos[1]
    if dispy > 0.5*leny: dispy -= leny
    if dispy < -0.5*leny: dispy += leny
    dispz = atom_pos[2]-line_pos[2]
    if dispz > 0.5*lenz: dispz -= lenz
    if dispz < -0.5*lenz: dispz += lenz
    dist = math.sqrt(dispx**2 + dispy**2 + dispz**2)
    return dist

############################################################
finput = "dislocation/practice_dislocation/v3_trial3/NEB_new/edge_b100_p110_NEB/next5/NEB_point3.data"
linepoints, fast_pid, slow_pid = get_dislocation(finput)
ztype = {1:28,2:27,3:22,4:40,5:72}
atoms = read_lammps_data(finput,atom_style="atomic",Z_of_type=ztype)
pos = atoms.get_positions()
atomic_number = atoms.get_atomic_numbers()
natoms = len(atoms)
cell = atoms.cell.cellpar()
rcut = 8.0

fast_aid = []
slow_aid = []
for pid in fast_pid:
    line_pos = linepoints[pid]
    for i in range(natoms):
        atom_pos = pos[i]
        dist = get_dist(atom_pos,line_pos,cell)
        if dist <= rcut:
            fast_aid.append(i)
for pid in slow_pid:
    line_pos = linepoints[pid]
    for i in range(natoms):
        atom_pos = pos[i]
        dist = get_dist(atom_pos,line_pos,cell)
        if dist <= rcut:
            slow_aid.append(i)

fast_aid = list(set(fast_aid))
slow_aid = list(set(slow_aid))

