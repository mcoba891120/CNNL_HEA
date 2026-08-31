import ase.io
from ase.io.lammpsdata import read_lammps_data
import numpy as np
import math
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()
itemsize = MPI.DOUBLE.Get_size()

ztype = {1:28,2:27,3:22,4:40,5:72}
atoms1 = read_lammps_data("HEA_init_screw1.data",atom_style="atomic",Z_of_type=ztype)
atoms2 = read_lammps_data("HEA_init_screw2.data",atom_style="atomic",Z_of_type=ztype)
pos1 = atoms1.get_positions()
pos2 = atoms2.get_positions()
cell = atoms1.cell.cellpar()
lenx = cell[0]
leny = cell[1]
lenz = cell[2]
natoms = len(atoms1)

num_iterations = natoms
tmp_id =[]
used_ids = set()  #用來存儲已經分配過的 ID
# 創建一個共享內存窗口
if rank == 0:
    nbytes = 1 * itemsize
else:
    nbytes = 0
win = MPI.Win.Allocate_shared(nbytes, itemsize, comm=comm)
buf, itemsize = win.Shared_query(0)
counter = np.ndarray(buffer=buf, dtype='int', shape=(1,))

# 每個進程計算分配的迭代次數
iterations_per_process = num_iterations // size
extra_iterations = num_iterations % size

start = rank * iterations_per_process + min(rank, extra_iterations)
end = start + iterations_per_process + (1 if rank < extra_iterations else 0)
for i in range(start, end):
    win.Lock(rank)
    counter[0] += 1
    string1 = "Alignment Progress: "+str(counter[0])+"/"+str(natoms)
    win.Unlock(rank)
    dispx = pos1[i][0]-pos2[i][0] 
    if dispx > 0.5*lenx: dispx -= lenx
    if dispx < -0.5*lenx: dispx += lenx
    dispy = pos1[i][1]-pos2[i][1]
    if dispy > 0.5*leny: dispy -= leny
    if dispy < -0.5*leny: dispy += leny
    dispz = pos1[i][2]-pos2[i][2]
    if dispz > 0.5*lenz: dispz -= lenz
    if dispz < -0.5*lenz: dispz += lenz
    dist = math.sqrt(dispx**2 + dispy**2 + dispz**2)
    if dist < 0.1:
        tmp_id.append(i)
        used_ids.add(i)  #確保這個 ID 被記錄
        string2 = " ID not change !"
    else:
        lowest_dist = 100.0
        lowest_id = 0
        for j in range(natoms):
            dispz = pos1[i][2]-pos2[j][2]
            if dispz > 0.5*lenz: dispz -= lenz
            if dispz < -0.5*lenz: dispz += lenz
            if abs(dispz) < 0.1:
                dispx = pos1[i][0]-pos2[j][0]
                if dispx > 0.5*lenx: dispx -= lenx
                if dispx < -0.5*lenx: dispx += lenx
                if abs(dispx) < 0.1:
                    dispy = pos1[i][1]-pos2[j][1]
                    if dispy > 0.5*leny: dispy -= leny
                    if dispy < -0.5*leny: dispy += leny
                    #if abs(dispy) <= lowest_dist and dispy < 0:
                    if abs(dispy) <= lowest_dist:
                        lowest_dist = abs(dispy)
                        lowest_id = j
            """
            dispx = pos1[i][0]-pos2[j][0]
            if dispx > lenx: dispx -= lenx
            dispy = pos1[i][1]-pos2[j][1]
            if dispy > leny: dispy -= leny
            dispz = pos1[i][2]-pos2[j][2]
            if dispz > lenz: dispz -= lenz
            dist[j] = math.sqrt(dispx**2 + dispy**2 + dispz**2)
            """
        #tmp_id.append(int(np.argmin(dist)))
        if i !=0 and lowest_id==0:
            print("Unable to Match Any Atoms!")
            comm.Abort()
        tmp_id.append(lowest_id)
        if lowest_id == i:
            string2 = " ID not change !"
        else:
            string2 = " ID change from "+str(i)+" to "+str(lowest_id)
    print(string1,string2)
        #if newid[i] != i:
            #print("ID change: "+str(i)+" ----> "+str(newid[i]))
tmp_id = comm.gather(tmp_id, root=0)
comm.Barrier()

if rank == 0:
    newid = np.concatenate(tmp_id)
    np.savetxt("Record_new_id.txt", newid, fmt='%i')
    if len(np.unique(newid)) < len(newid):
        print(str(len(newid))+"/"+str((len(np.unique(newid)))))
        print("ID comflict has Determined!")
    else:
        print("NEB ID Alignment Completed!")


