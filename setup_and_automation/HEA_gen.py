# switch half of the Ni into Co and half Ni into Zr
#
# Seed is a CLI arg (default 12345678, matching the original hardcoded
# value) rather than hardcoded, since some past session names encode the
# seed actually used, e.g. "var13_13500_27873145" was generated with
# seed=27873145 — that run is not reproducible with the old default.
import sys
from ase.io import vasp
from ase.io import lammpsdata
import random
import numpy as np

session_name = str(sys.argv[1])
total_atom = int(sys.argv[2])
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 12345678
Ni_end = total_atom // 2
atom_num = total_atom // 4


NiTi = vasp.read_vasp(f"./structure/{session_name}.pos")


def random_index(start, end, num, seed):
    random.seed(seed)
    index = random.sample(range(start, end), num)
    index = np.array(index)
    index.sort()
    index = index.tolist()
    return index


index_NiCo = random_index(0, Ni_end, atom_num, seed)
for i in index_NiCo:
    NiTi[i].symbol = "Co"

index_NiZr = random_index(Ni_end, total_atom, atom_num, seed)
for i in index_NiZr:
    NiTi[i].symbol = "Zr"

print(NiTi.get_chemical_formula())
# vasp.write_vasp(f"{session_name}.pos", NiTi)
lammpsdata.write_lammps_data(
    f"{session_name}.lmp", NiTi, specorder=["Ni", "Co", "Ti", "Zr"], masses=True
)