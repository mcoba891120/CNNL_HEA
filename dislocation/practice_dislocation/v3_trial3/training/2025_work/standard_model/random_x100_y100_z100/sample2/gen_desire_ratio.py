import ase.io, ase.io.vasp, ase.io.lammpsdata,copy, random

atoms = ase.io.read("../POSCAR")

Ni_L = [x for x in range(len(atoms)) if atoms[x].symbol=='Ni']
Ti_L = [x for x in range(len(atoms)) if atoms[x].symbol=='Ti']


num_Co = int(len(Ni_L)/2)
num_Zr = int(len(Ti_L)/3)
num_Hf = num_Zr

atoms_curr = copy.deepcopy(atoms)
Co_L  = random.sample(Ni_L, num_Co)
for cc in Co_L:
   atoms_curr[cc].symbol = 'Co'
Zr_L  = random.sample(Ti_L, num_Zr)
for cc in Zr_L:
   atoms_curr[cc].symbol = 'Zr'

new_Ti_L = [x for x in range(len(atoms_curr)) if atoms_curr[x].symbol=='Ti']
Hf_L  = random.sample(new_Ti_L, num_Hf)
for cc in Hf_L:
   atoms_curr[cc].symbol = 'Hf'
ase.io.lammpsdata.write_lammps_data("HEA_init.data", atoms_curr, specorder=['Ni','Co','Ti','Zr','Hf'], units='metal', atom_style='atomic')
