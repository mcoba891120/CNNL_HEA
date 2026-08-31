from ase.io import read, write
import ase.io.lammpsdata
from ase import Atoms
import numpy as np

#讀POSCAR檔案
atoms = read("POSCAR")

#擷取原子結構中所有原子的化學符號
symbols = atoms.get_chemical_symbols()
#各元素個數
element_num = len(symbols) // 4

#分離Ni和Ti
a_site = [symbol for symbol in symbols if symbol == 'Ni']
b_site = [symbol for symbol in symbols if symbol != 'Ni']

for i in range(element_num):
    a_site[i] = 'Co'
for i in range(element_num):
    b_site[i] = 'Zr'

#打亂
np.random.shuffle(a_site)
np.random.shuffle(b_site)

new_symbols = a_site + b_site

#更新原子符號
atoms.set_chemical_symbols(new_symbols)

#將修改後的結構寫入新的文件
ase.io.lammpsdata.write_lammps_data("POSCAR_modified.data", atoms, specorder = ['Ni','Co','Ti','Zr'], units = 'metal', atom_style = 'atomic')
