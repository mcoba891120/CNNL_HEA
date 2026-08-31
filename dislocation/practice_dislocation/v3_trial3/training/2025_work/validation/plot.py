import numpy as np
import matplotlib.pyplot as plt

tEQM,tEMM,tNatom = np.loadtxt("parity_energy.txt",unpack=True)
tFQM,tFMM = np.loadtxt("parity_force.txt",unpack=True)
#vEQM,vEMM,vNatom = np.loadtxt("valid_parity_energy.txt",unpack=True)
#vFQM,vFMM = np.loadtxt("valid_parity_force.txt",unpack=True)
normtEQM = np.true_divide(tEQM,tNatom)
normtEMM = np.true_divide(tEMM,tNatom)
#normvEQM = np.true_divide(vEQM,vNatom)
#normvEMM = np.true_divide(vEMM,vNatom)


plt.plot(normtEQM, normtEQM, color='black',linewidth=0.5)
plt.scatter(normtEQM, normtEMM, marker='o', color='red', s=5)
#plt.scatter(normvEQM, normvEMM, marker='o', color='green', s=5)
plt.xlabel('DFT Energy/atom (eV)')
plt.ylabel('SNAP Energy/atom (eV)')
plt.show()


plt.plot(tFQM, tFQM, color='black',linewidth=0.5)
plt.scatter(tFQM, tFMM, marker='o', color='red', s=5)
#plt.scatter(vFQM, vFMM, marker='o', color='green', s=5)
plt.xlabel('DFT Force (eV/A)')
plt.ylabel('SNAP Force (eV/A)')
plt.show()

