import ase.io
from ase.io.lammpsrun import read_lammps_dump_text
from ase.io.lammpsdata import read_lammps_data
import numpy as np
import math

nframes = 11
ztype = {1:28,2:27,3:22,4:40,5:72}
atoms = read_lammps_data("HEA_opt_edge1.data",atom_style="atomic",Z_of_type=ztype)

for i in range(nframes):
    dump = "dump.neb."+str(i+1)
    tmp = read_lammps_dump_text(open(dump,'r'),index=-1)
    tmp_pos = tmp.get_positions()
    atoms.set_positions(tmp_pos)
    ase.io.write("NEB_point"+str(i+1)+".data",atoms,format="lammps-data",specorder=["Ni","Co","Ti","Zr","Hf"],masses=True)

