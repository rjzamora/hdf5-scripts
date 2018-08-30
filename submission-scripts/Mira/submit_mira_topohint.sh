#!/bin/bash

WALLTIME="-t 30"
N="-n 128"
MACHINE="--machine mira"
EXECNAME="--execname /home/zamora/hdf5_root_dir/exerciser/build-theta-opt/hdf5Exerciser-mira-opt"
OUTROOT="--outroot /projects/datascience/rzamora/exerciser/ccio-hdf5"
CCIO=""
ROMIO="--romio_ind --romio_col"
TOPO="--topology"
DIMS="--dim 3"

echo "Calling submit_exerciser.py"
qsub ${WALLTIME} ${N} --mode script submit_exerciser.py ${ROMIO} ${CCIO} ${TOPO} ${DIMS} ${PPN} ${MACHINE} ${PPN} ${MACHINE} ${EXECNAME} ${OUTROOT}
echo "done calling qsub."
