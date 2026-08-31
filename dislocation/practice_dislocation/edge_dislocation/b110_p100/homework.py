from ase.io import read, write
import ase.io.lammpsdata
from ase import Atoms
import numpy as np

#讀NiTi.lmp檔案
atoms = read("POSCAR")

#擷取原子結構中所有原子的化學符號
symbols = atoms.get_chemical_symbols()

#統計Ni和Ti原子的數量
ni_count = symbols.count('Ni')
ti_count = symbols.count('Ti')

#讓Ni和Co各佔原始Ni原子數量的一半
a_site = ['Ni'] * (ni_count // 2) + ['Co'] * (ni_count // 2)

#讓Ti和Zr和Hf各佔原始Ti原子數量的三分之一
b_site = ['Ti'] * (ti_count // 3) + ['Zr'] * (ti_count // 3) + ['Hf'] * (ti_count - 2 * (ti_count // 3))



#打亂
np.random.shuffle(a_site)
np.random.shuffle(b_site)

new_symbols = a_site + b_site

#更新原子符號
atoms.set_chemical_symbols(new_symbols)

#將修改後的結構寫入新的文件
ase.io.lammpsdata.write_lammps_data("POSCAR_modified.data", atoms, specorder = ['Ni','Co','Ti','Zr','Hf'], units = 'metal', atom_style = 'atomic')
