# switch half of the Ni into Co and half Ni into Zr
import sys
from ase.io import vasp
from ase.io import lammpsdata
import random
import numpy as np

session_name = str(sys.argv[1])
num_atoms = int(sys.argv[2])
NiTi = vasp.read_vasp(f"{session_name}")


def random_index(start, end, count, exclude=set()):
    indices = []
    random.seed(12345678)
    while len(indices) < count:
        idx = random.randint(start, end - 1)
        if idx not in exclude:
            indices.append(idx)
            exclude.add(idx)
    return indices


# Randomly replace half of the Ni atoms with Co
num_ni_to_replace = len(NiTi) // 4
ni_indices = [i for i, atom in enumerate(NiTi) if atom.symbol == 'Ni']
random.shuffle(ni_indices)
for i in ni_indices[:num_ni_to_replace]:
    NiTi[i].symbol = 'Co'

# Randomly replace one third of the Ti atoms with Zr and another third with Hf
num_ti = len(NiTi) // 2
num_ti_to_replace_zr = num_ti // 3
num_ti_to_replace_hf = num_ti // 3

ti_indices = [i for i, atom in enumerate(NiTi) if atom.symbol == 'Ti']
random.shuffle(ti_indices)

# Replace one third with Zr and track the indices
index_TiZr = random_index(0, num_ti, num_ti_to_replace_zr)
for i in index_TiZr:
    NiTi[num_atoms // 2 + i].symbol = 'Zr'

# Replace another third with Hf, avoiding indices used for Zr
index_TiHf = random_index(0, num_ti, num_ti_to_replace_hf, set(index_TiZr))
for i in index_TiHf:
    NiTi[num_atoms // 2 + i].symbol = 'Hf'

#print(atoms.get_chemical_formula())
#vasp.write_vasp(f"{session_name}.pos", NiTi)
lammpsdata.write_lammps_data(
    f"{session_name}.lmp", NiTi, specorder=["Ni", "Co", "Ti", "Zr", "Hf"], masses=True
)
