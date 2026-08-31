import numpy as np
import os
import sys
import math
from ase.io import read
#from ase.calculators.lammpsrun import LAMMPS
from ase.calculators.lammpslib import LAMMPSlib
######### Custom Setting #############
# original cluster path removed (pointed at a collaborator's account) —
# the DFT training set itself is not included in this repo, see potentials/NOTES.md
traindir = "../../data"  # not present in this repo
trainsets = [
"NiCoTiZrHf/valid/B2_100_hydro_0%/lmp",
"NiCoTiZrHf/valid/B2_100_hydro_m5%/lmp",
"NiCoTiZrHf/valid/B2_100_hydro_p5%/lmp",
"NiCoTiZrHf/valid/B2_100_hydro_m10%/lmp",
"NiCoTiZrHf/valid/B2_100_hydro_p10%/lmp",
"NiCoTiZrHf/valid/B2_110_hydro_0%/lmp",
"NiCoTiZrHf/valid/B2_110_hydro_m5%/lmp",
"NiCoTiZrHf/valid/B2_110_hydro_p5%/lmp",
"NiCoTiZrHf/valid/B2_110_hydro_m10%/lmp",
"NiCoTiZrHf/valid/B2_110_hydro_p10%/lmp",
"NiCoTiZrHf/valid/B2_111_hydro_0%/lmp",
"NiCoTiZrHf/valid/B2_111_hydro_m5%/lmp",
"NiCoTiZrHf/valid/B2_111_hydro_p5%/lmp",
"NiCoTiZrHf/valid/B2_111_hydro_m10%/lmp",
"NiCoTiZrHf/valid/B2_111_hydro_p10%/lmp",
"NiCoTiZrHf/valid/hydro_strain_5%_SE/lmp",
"NiCoTiZrHf/valid/hydro_strain_5%_new_SE/lmp",
"NiCoTiZrHf/valid/hydro_strain_10%_SE/lmp",
"NiCoTiZrHf/valid/hydro_strain_10%_new_SE/lmp",
#"NiCoTiZrHf/valid/amorphous_MD/lmp",
#"NiCoTiZrHf/valid/defects_vacancy_2%_MD/lmp",
#"NiCoTiZrHf/valid/defects_vacancy_5%_MD/lmp",
#"NiCoTiZrHf/valid/defects_interstitial_2%_MD/lmp",
#"NiCoTiZrHf/valid/defects_interstitial_5%_MD/lmp",
#"NiCoTiZrHf/valid/defects_unmatched_MD/lmp",
#"NiCoTiZrHf/valid/Zr_swap_5%_MD/lmp",
#"NiCoTiZrHf/valid/Zr_swap_10%_MD/lmp",
#"NiCoTiZrHf/valid/Zr_swap_15%_MD/lmp",
#"NiCoTiZrHf/valid/Zr_swap_20%_MD/lmp",
#"NiCoTiZrHf/valid/Zr_swap_25%_MD/lmp",
#"NiCoTiZrHf/valid/SF_100_MIN/lmp",
#"NiCoTiZrHf/valid/SF_100_modify_MIN/lmp",
#"NiCoTiZrHf/valid/SF_100_modify_SE/lmp",
#"NiCoTiZrHf/valid/SF_110_MIN/lmp",
#"NiCoTiZrHf/valid/SF_110_modify_MIN/lmp",
#"NiCoTiZrHf/valid/SF_110_modify_SE/lmp"
             ]

elements = ['Ni','Co','Ti','Zr','Hf']
#######################################

ztypes = {1:28,2:27,3:22,4:40,5:72}
atom_types = {'Ni':1,'Co':2,'Ti':3,'Zr':4,'Hf':5}
#"""
headers = ['units metal',
           'atom_style atomic',
           'atom_modify map yes']
cmds = ['pair_style snap',
        'pair_coeff * * ../HEA_v7_trial6.snapcoeff ../HEA_v7_trial6.snapparam Ni Co Ti Zr Hf',
        'neigh_modify one 5000']
lammps = LAMMPSlib(atom_types=atom_types,lammps_header=headers,lmpcmds=cmds)
"""
parameters = { 
               'box': 'tilt large',
               'pair_style':'snap',
               'pair_coeff':['* * ../HEA_v7_trial6.snapcoeff ../HEA_v7_trial6.snapparam Ni Co Ti Zr Hf'],
               'mass':['1 58.6934','2 58.933195','3 47.867','4 91.224','5 178.49']
             }
files = {"../HEA_v7_trial6.snapcoeff","../HEA_v7_trial6.snapparam"}
lammps = LAMMPS(files=files, **parameters)
"""
#######################################
counte = 0
countf = 0
counta = 0
counta_small = 0
dev_e = 0.0
dev_f = 0.0
dev_v = 0.0

parity_e = open("parity_energy.txt","w")
parity_f = open("parity_force.txt","w")
angle_f = open("force_angle.txt","w")

nconfigs = np.zeros(int(len(trainsets)))
for nset in range(len(trainsets)):
    nconfigs[nset] = 0
    for file in os.listdir(str(traindir)+"/"+str(trainsets[nset])):
        if ".data" in file:
            nconfigs[nset] += 1
    EQM = np.loadtxt(str(traindir)+"/"+str(trainsets[nset])+"/energy.txt")
#    VQM = np.loadtxt(str(scratch_dir)+"/"+str(trainsets[nset])+"/stress.txt")
    
    for i in range(int(nconfigs[nset])):
        print(str(trainsets[nset])+"  ("+str(i+1)+"/"+str(int(nconfigs[nset]))+")")
        datafile = str(traindir)+"/"+str(trainsets[int(nset)])+"/"+str(i+1)+".data"
        atoms = read(datafile,format="lammps-data",Z_of_type=ztypes,style='atomic')
        atoms.calc = lammps
        natoms = len(atoms)
        pe = atoms.get_potential_energy()
        atomf = atoms.get_forces()
        FQM = np.loadtxt(str(traindir)+"/"+str(trainsets[int(nset)])+"/step_"+str(i+1)+"_force.txt")
        if int(nconfigs[nset]) == 1:
            dev_e += ((EQM-pe)/natoms)**2
            parity_e.write(str(EQM)+" "+str(pe)+" "+str(natoms)+"\n")
        else:
            dev_e += ((EQM[int(i)]-pe)/natoms)**2
            parity_e.write(str(EQM[int(i)])+" "+str(pe)+" "+str(natoms)+"\n")
        counte += 1
#        parity_v.write(str(VQM[int(i)][0])+" "+str(stress[0]*pref)+"\n")
#        parity_v.write(str(VQM[int(i)][1])+" "+str(stress[1]*pref)+"\n")
#        parity_v.write(str(VQM[int(i)][2])+" "+str(stress[2]*pref)+"\n")
#        parity_v.write(str(VQM[int(i)][3])+" "+str(stress[3]*pref)+"\n")
#        parity_v.write(str(VQM[int(i)][4])+" "+str(stress[4]*pref)+"\n")
#        parity_v.write(str(VQM[int(i)][5])+" "+str(stress[5]*pref)+"\n")
#        for k in range(6):
#            dev_v += (VQM[int(i)][int(k)]-stress[int(k)]*pref)**2
        for j in range(natoms):
            #print(str(atomf[j][0])+" "+str(atomf[j][1])+" "+str(atomf[j][2]))
            for k in range(3):
                dev_f += (FQM[j][k]-atomf[j][k])**2
                countf += 1
                parity_f.write(str(FQM[j][k])+" "+str(atomf[j][k])+"\n")
            v1 = np.array([FQM[j][0],FQM[j][1],FQM[j][2]])
            v2 = np.array([atomf[j][0],atomf[j][1],atomf[j][2]])
            v1_u = v1/(np.linalg.norm(v1))
            v2_u = v2/(np.linalg.norm(v2))
            angle = np.rad2deg(np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0)))
            angle_f.write(str(angle)+"\n")
            counta += 1
            if (angle < 20):
                counta_small += 1

        #########################################

avgdev_e = math.sqrt(dev_e/counte)
avgdev_f = math.sqrt(dev_f/countf)
#avgdev_v = math.sqrt(dev_v)/counte
print("Energy error/atoms = "+str('%.6f' % (avgdev_e))+" eV")
print("Force error/atoms = "+str('%.6f' % (avgdev_f))+" eV/A")
print("Probability of Angle small than 20 deg = "+str('%.6f' % (100*counta_small/counta))+"%")
#print("Stress error = "+str('%.6f' % (avgdev_v))+" kPa")
