#!/bin/bash

module unload darshan
module load cray-hdf5-parallel/1.10.2.0

#WALLTIME="-t 15"
WALLTIME="-t 120"
#N="-n 4"
N="-n 1024"
PPN="--ppn 16"
MACHINE="--machine theta"
EXECNAME="--execname /lus-projects/datascience/rzamora/exerciser/cray-hdf5-1.10.2.0/exerciser/hdf5Exerciser.exe"
OUTROOT="--outroot /lus-projects/datascience/rzamora/exerciser/cray-hdf5-1.10.2.0"
#LUSTRE="--lfs_size 1 --lfs_count 2"
LUSTRE="--lfs_size 8 --lfs_count 48"
ROMIO=""
CRAY="--cray_ind --cray_col"
TOPO=""
DIMS="--dim 3 --nsizes 4"

echo "Calling submit_exerciser.py"
#qsub -q debug-flat-quad ${WALLTIME} ${N} submit_exerciser.py ${LUSTRE} ${ROMIO} ${CRAY} ${TOPO} ${DIMS} ${PPN} ${MACHINE} ${PPN} ${MACHINE} ${EXECNAME} ${OUTROOT}
qsub ${WALLTIME} ${N} submit_exerciser.py ${LUSTRE} ${ROMIO} ${CRAY} ${TOPO} ${DIMS} ${PPN} ${MACHINE} ${PPN} ${MACHINE} ${EXECNAME} ${OUTROOT}
echo "done calling qsub."
