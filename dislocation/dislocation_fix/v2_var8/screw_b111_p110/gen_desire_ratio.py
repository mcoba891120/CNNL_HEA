import ase.io, ase.io.vasp, ase.io.lammpsdata,copy, random

atoms = ase.io.read("../screw_POSCAR_b111_p110")

Ni_L = [x for x in range(len(atoms)) if atoms[x].symbol=='Ni']
Ti_L = [x for x in range(len(atoms)) if atoms[x].symbol=='Ti']


num_Co = int(len(Ni_L)/2)
num_Zr = int(len(Ti_L)/2)

atoms_curr = copy.deepcopy(atoms)
Co_L  = random.sample(Ni_L, num_Co)
for cc in Co_L:
   atoms_curr[cc].symbol = 'Co'
Zr_L  = random.sample(Ti_L, num_Zr)
for cc in Zr_L:
   atoms_curr[cc].symbol = 'Zr'

ase.io.lammpsdata.write_lammps_data("HEA_init_B2.data", atoms_curr, specorder=['Ni','Co','Ti','Zr'], units='metal', atom_style='atomic')
