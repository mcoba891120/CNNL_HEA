import os
import numpy as np
import ase.io
from ase.io.lammpsdata import read_lammps_data
import math
from operator import itemgetter
from ovito.io import import_file, export_file
from ovito.modifiers import DislocationAnalysisModifier
from ovito.data import DislocationNetwork
from ovito.io import import_file
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
finput = "./next5/NEB_point9.data"
linepoints, fast_pid, slow_pid = get_dislocation(finput)
ztype = {1:28,2:27,3:22,4:40,5:72}
atoms = read_lammps_data(finput,atom_style="atomic",Z_of_type=ztype)
pos = atoms.get_positions()
atomic_number = atoms.get_atomic_numbers()
original_atomic_number = atomic_number.copy()
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

new_atoms = atoms
print(str(len(fast_aid))+" of atoms have been found nearby fastest dislocation line.")
Ni_count = 0
Co_count = 0
Ti_count = 0
Zr_count = 0
Hf_count = 0
# {1:28,2:27,3:22,4:40,5:72}
for i in fast_aid:
    if atomic_number[i] == 28: Ni_count+=1
    if atomic_number[i] == 27: Co_count+=1
    if atomic_number[i] == 22: Ti_count+=1
    if atomic_number[i] == 40: Zr_count+=1
    if atomic_number[i] == 72: Hf_count+=1
    atomic_number[i] = 47 # change type for checking
print("Ratio of Ni: "+str(Ni_count/len(fast_aid)))
print("Ratio of Co: "+str(Co_count/len(fast_aid)))
print("Ratio of Ti: "+str(Ti_count/len(fast_aid)))
print("Ratio of Zr: "+str(Zr_count/len(fast_aid)))
print("Ratio of Hf: "+str(Hf_count/len(fast_aid)))
print("\n")   

print(str(len(slow_aid))+" of atoms have been found nearby slowest dislocation line.")
Ni_count = 0
Co_count = 0
Ti_count = 0
Zr_count = 0
Hf_count = 0
for i in slow_aid:
    if atomic_number[i] == 28: Ni_count+=1
    if atomic_number[i] == 27: Co_count+=1
    if atomic_number[i] == 22: Ti_count+=1
    if atomic_number[i] == 40: Zr_count+=1
    if atomic_number[i] == 72: Hf_count+=1
    atomic_number[i] = 79 # change type for checking
print("Ratio of Ni: "+str(Ni_count/len(slow_aid)))
print("Ratio of Co: "+str(Co_count/len(slow_aid)))
print("Ratio of Ti: "+str(Ti_count/len(slow_aid)))
print("Ratio of Zr: "+str(Zr_count/len(slow_aid)))
print("Ratio of Hf: "+str(Hf_count/len(slow_aid)))
print("\n")   

### export checking file
new_atoms.set_atomic_numbers(atomic_number)
ase.io.write("dislocation_checking.data",new_atoms,format="lammps-data",specorder=["Ni","Co","Ti","Zr","Hf","Ag","Au"],masses=True)

from ovito.io import import_file
from ovito.data import DataCollection
import numpy as np
from collections import Counter
import WarrenCowleyParameters as wc

pipeline = import_file(finput)

# --- 選取 fast_aid ---
pipeline.modifiers.clear()
pipeline.modifiers.append(lambda frame, data: data.particles_.create_property('Selection', data=np.isin(np.arange(data.particles.count), fast_aid).astype(int)))
mod = wc.WarrenCowleyParameters(nneigh=[0, 14], only_selected=True)
pipeline.modifiers.append(mod)
data_fast = pipeline.compute()
wc_fast = data_fast.attributes["Warren-Cowley parameters"]

# --- 選取 slow_aid ---
pipeline.modifiers.clear()
pipeline.modifiers.append(lambda frame, data: data.particles_.create_property('Selection', data=np.isin(np.arange(data.particles.count), slow_aid).astype(int)))
mod = wc.WarrenCowleyParameters(nneigh=[0, 14], only_selected=True)
pipeline.modifiers.append(mod)
data_slow = pipeline.compute()
wc_slow = data_slow.attributes["Warren-Cowley parameters"]

# Step 3: 計算元素比例並寫檔案
z2el = {28: "Ni", 27: "Co", 22: "Ti", 40: "Zr", 72: "Hf"}

def get_composition(aid_list, numbers, z2el):
    elements = [z2el[numbers[i]] for i in aid_list if numbers[i] in z2el]
    counter = Counter(elements)
    total = sum(counter.values())
    order = ["Ni", "Co", "Ti", "Zr", "Hf"]  # 指定固定順序
    comp_str = ""
    for elem in order:
        ratio = counter[elem] / total if elem in counter else 0.0
        comp_str += f"{elem}: {ratio:.3f}  "
    return comp_str.strip()

with open("wc_summary.txt", "w") as f:
    f.write("=== Fast Region ===\n")
    f.write("Composition: " + get_composition(fast_aid, original_atomic_number, z2el) + "\n")
    f.write("Warren-Cowley parameters:\n")
    f.write(str(wc_fast[0]) + "\n\n")

    f.write("=== Slow Region ===\n")
    f.write("Composition: " + get_composition(slow_aid, original_atomic_number, z2el) + "\n")
    f.write("Warren-Cowley parameters:\n")
    f.write(str(wc_slow[0]) + "\n")

print("Warren-Cowley analysis completed for both fast and slow regions.")
