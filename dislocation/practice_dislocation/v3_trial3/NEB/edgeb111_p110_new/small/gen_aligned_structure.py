import ase.io
from ase.io.lammpsdata import read_lammps_data
import numpy as np
import math

#newid = np.loadtxt("Record_new_id.txt",dtype="int")
ztype = {1:28,2:27,3:22,4:40,5:72}
atoms1 = read_lammps_data("HEA_init_edge1.data",atom_style="atomic",Z_of_type=ztype)
atoms2 = read_lammps_data("HEA_init_edge2.data",atom_style="atomic",Z_of_type=ztype)
pos1 = atoms1.get_positions()
pos2 = atoms2.get_positions()
atomic_number1 = atoms1.get_atomic_numbers() 
natoms = len(atoms1)
cell = atoms1.cell.cellpar()
lenx = cell[0]
leny = cell[1]
lenz = cell[2]
newid = [i for i in range(natoms)]
org_dist = 0.0
new_dist = 0.0
for i in range(natoms):
    ####################
    dispx = pos1[i][0]-pos2[i][0]
    if dispx > 0.5*lenx: dispx -= lenx
    if dispx < -0.5*lenx: dispx += lenx
    dispy = pos1[i][1]-pos2[i][1]
    if dispy > 0.5*leny: dispy -= leny
    if dispy < -0.5*leny: dispy += leny
    dispz = pos1[i][2]-pos2[i][2]
    if dispz > 0.5*lenz: dispz -= lenz
    if dispz < -0.5*lenz: dispz += lenz
    org_dist += math.sqrt(dispx**2 + dispy**2 + dispz**2)
    ####################
    dispx = pos2[newid[i]][0]-pos1[i][0]
    if dispx > 0.5*lenx: dispx -= lenx
    if dispx < -0.5*lenx: dispx += lenx
    dispy = pos2[newid[i]][1]-pos1[i][1]
    if dispy > 0.5*leny: dispy -= leny
    if dispy < -0.5*leny: dispy += leny
    dispz = pos2[newid[i]][2]-pos1[i][2]
    if dispz > 0.5*lenz: dispz -= lenz
    if dispz < -0.5*lenz: dispz += lenz
    new_dist += math.sqrt(dispx**2 + dispy**2 + dispz**2)
print("Orginal Total Displacement: "+str(org_dist))
print("New Total Displacement: "+str(new_dist))

new_pos = np.zeros([natoms,3])
for i in range(natoms):
    #print("Change ID from "+str(orgid[i])+" to "+str(newid[i]))
    new_pos[i][0] = pos2[newid[i]][0]
    new_pos[i][1] = pos2[newid[i]][1]
    new_pos[i][2] = pos2[newid[i]][2]
    
atoms2.set_atomic_numbers(atomic_number1)
atoms2.set_positions(new_pos)
ase.io.write("HEA_init_edge3.data",atoms2,format="lammps-data",specorder=["Ni","Co","Ti","Zr","Hf"],masses=True)

