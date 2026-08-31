# Standard Python libraries
from copy import deepcopy
import datetime
import numpy as np
import matplotlib.pyplot as plt
import atomman as am
import atomman.unitconvert as uc

# Show atomman version
print('atomman version =', am.__version__)

# Show date of Notebook execution
print('Notebook executed on', datetime.date.today())

# Load dislocation configurations that were previously constructed using Dislocation class
base_system = am.load('atom_dump', 'dislocation/practice_dislocation/v3_trial3/NEB_new/screw_b100_p110_NEB/large_nomd/perfect_B2.data')
disl_system = am.load('atom_dump', 'dislocation/practice_dislocation/v3_trial3/NEB_new/screw_b100_p110_NEB/large_nomd/dump.neb.1')
alat = uc.set_in_units(4.05, 'Å')
burgers = np.array([0.0, alat / 2**0.5, 0.0])
base_neighbors = base_system.neighborlist(cutoff = 0.9*alat)
disl_neighbors = disl_system.neighborlist(cutoff = 0.9*alat)
dd = am.defect.DifferentialDisplacement(base_system, disl_system, neighbors=disl_neighbors, reference=0)

print(dd.ddvectors.shape)
print(dd.ddvectors)

print(dd.arrowcenters.shape)
print(dd.arrowcenters)

print(dd.arrowuvectors.shape)
print(dd.arrowuvectors)

# Create dict of common plotting parameter values for all
params = {}
params['ddmax'] = np.linalg.norm(burgers) / 4     # Useb|/4 for a/2<110> fcc dislocations
params['plotxaxis'] = 'y'                         # Align plotting x-axis with the Cartesian y-axis, which is aligned with dislocation m-axis
params['plotyaxis'] = 'z'                         # Align plotting y-axis with the Cartesian z-axis, which is aligned with dislocation n-axis
params['figsize'] = 10                            # Plots will be "regular" if only one size value is given

params['xlim'] = (-20, 20)                        # Plotting limits for the plotting x-axis.  Large as this is along the slip plane
params['ylim'] = (-5, 5)                          # Plotting limits for the plotting y-axis.  Small as this is perpendicular to the slip plane
params['zlim'] = (0.01, alat * 6**0.5 / 2 + 0.01)   # Should be one periodic length of the crystal along the dislocation line direction

params['arrowwidth'] = 1/50                       # Made bigger to make arrows easier to see
params['arrowscale'] = 2.4                        # Typically chosen to make arrows of length ddmax touch the corresponding atom circles

dd.plot('x', **params)
plt.title('x component')
plt.show()

dd.plot('y', **params)
plt.title('y component')
plt.show()

dd.plot('z', **params)
plt.title('z component')
plt.show()

dd.plot(burgers, **params)
plt.title('Parallel to Burgers')
plt.show()

dd.plot('projection', **params)
plt.title('In-plane projection')
plt.show()