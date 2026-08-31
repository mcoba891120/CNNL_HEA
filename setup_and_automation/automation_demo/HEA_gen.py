# switch half of the Ni into Co and half Ni into Zr
import sys
from ase.io import vasp
from ase.io import lammpsdata
import random
import numpy as np

session_name = str(sys.argv[1]) 
total_atom = int(sys.argv[2])
Ni_end = total_atom // 2
atom_num = total_atom // 4


NiTi = vasp.read_vasp(f"./structure/{session_name}.pos")


def random_index(start, end, num):
    random.seed(12345678)
    index = random.sample(range(start, end), num)
    index = np.array(index)
    index.sort()
    index = index.tolist()
    return index


index_NiCo = random_index(0, Ni_end, atom_num)
for i in index_NiCo:
    NiTi[i].symbol = "Co"

index_NiZr = random_index(Ni_end, total_atom, atom_num)
for i in index_NiZr:
    NiTi[i].symbol = "Zr"

print(NiTi.get_chemical_formula())
# vasp.write_vasp(f"{session_name}.pos", NiTi)
lammpsdata.write_lammps_data(
    f"{session_name}.lmp", NiTi, specorder=["Ni", "Co", "Ti", "Zr"], masses=True
)