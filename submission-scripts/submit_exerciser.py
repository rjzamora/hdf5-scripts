#!/usr/bin/env python
#COBALT -A datascience
###COBALT -n 4
###COBALT -t 30
###COBALT -q debug-cache-flat

# Load python modules
import subprocess
import os.path
import os
import time
import glob
import argparse

# ---------------------------------------------------------------------------- #
#
# This script submits an exerciser run with desired settings
# (set using argparse)
#
# Author: Richard J Zamora, rzamora@anl.gov
# Last Update: August 16th 2018
#
# ---------------------------------------------------------------------------- #

# Use argparse to get desired job details
parser = argparse.ArgumentParser(); notset = "-1"
parser.add_argument("--machine", dest="machine", default=notset,
                    help="machine name (theta, vest, mac) [Default: $THIS_MACHINE env]")
parser.add_argument("--execname", dest="execname", default=notset,
                    help="exerciser executable path [Default: machine dependent]")
parser.add_argument("--outroot", dest="outroot", default=notset,
                    help="root path for run directory [Default: machine dependent]")
parser.add_argument("--nodes", dest="nodes", default="1",
                    help="Node count, ignored if this is a batch script  [Default: 1]")
parser.add_argument("--ppn", dest="ppn", default="1",
                    help="number of mpi ranks to use per node [Default: 1]")
parser.add_argument("--lfs_size", dest="lfs_size", default="1",
                    help="Lustre stripe size (MB) (theta only) [Default: 8]")
parser.add_argument("--lfs_count", dest="lfs_count", default="1",
                    help="Lustre stripe count (theta only) [Default: 1]")
parser.add_argument("--dim", dest="dim", default="1",
                    help="Dimension of the double-precision dataset  [Default: 1]")
parser.add_argument("--mpi", dest="mpi", default="0",
                    help="mpi version to use (only used on theta for now)  [Default: 0]")
parser.add_argument("--ccio", dest="ccio", action="store_true", default=False,
                    help="Test one-sided custom-collective I/O [Default: False]")
parser.add_argument("--async", dest="async", action="store_true", default=False,
                    help="Test ccio with asynchronous I/O [Default: False]")
parser.add_argument("--romio_col", dest="romio_col", action="store_true", default=False,
                    help="Test ROMIO collective I/O  default [Default: False]")
parser.add_argument("--romio_ind", dest="romio_ind", action="store_true", default=False,
                    help="Test ROMIO independent I/O default [Default: False]")
parser.add_argument("--cray_col", dest="cray_col", action="store_true", default=False,
                    help="Test CRAY-MPICH collective I/O  default (theta only) [Default: False]")
parser.add_argument("--cray_ind", dest="cray_ind", action="store_true", default=False,
                    help="Test CRAY-MPICH independent I/O  default (theta only) [Default: False]")
parser.add_argument("--minb", dest="minb", default=notset,
                    help="Number of elements in each dim (for smallest buffer size) [Default: dim dependent]")
parser.add_argument("--bmult", dest="bmult", default=notset,
                    help="Multiplication factor for buffer size between runs [Default: dim dependent]")
parser.add_argument("--nsizes", dest="nsizes", default=notset,
                    help="How many local buffer sizes to try [Default: dim dependent]")
parser.add_argument("--perf", dest="perf", action="store_true", default=False,
                    help="Print performance counters for CCIO [Default: False]")
parser.add_argument("--debug", dest="debug", action="store_true", default=False,
                    help="Set CCIO debug env variable [Default: False]")
parser.add_argument("--topology", dest="topology", action="store_true", default=False,
                    help="Compare topology-aware cb agg selection [Default: False]")
parser.add_argument("--rshift", dest="rshift", action="store_true", default=False,
                    help="Shift ranks by ppn for read (avoid cache effects) [Default: False]")
parser.add_argument("--naggs", dest="naggs", default="0",
                    help="Override the number of aggregators chosen by the system/algorithm [Default: 0]")
args = parser.parse_args()
machname = args.machine
execname = args.execname
outroot = args.outroot
execname = args.execname
nodes = int(args.nodes)
ppn = int(args.ppn)
lfs_size = int(args.lfs_size)
lfs_count = int(args.lfs_count)
dim = int(args.dim)
mpiversion = args.mpi
ccio = args.ccio
async = args.async
romio_col = args.romio_col
romio_ind = args.romio_ind
cray_col = args.cray_col
cray_ind = args.cray_ind
minb = args.minb
bmult = args.bmult
nsizes = args.nsizes
if args.minb != notset: minb = int(args.minb)
if args.bmult != notset: bmult = int(args.bmult)
if args.nsizes != notset: nsizes = int(args.nsizes)
perf = args.perf
debug = args.debug
topology = args.topology
rshift = args.rshift
topohint = False
if topology and (not ccio):
	topology = False
	topohint = True
naggs = int(args.naggs)

# ---------------------------------------------------------------------------- #
#  Setup the basic properties of the run
# ---------------------------------------------------------------------------- #

# Detect the machine (THIS_MACHINE env var should be set)
if machname == notset: machname = os.environ['THIS_MACHINE']
if not (machname in ["mac", "theta", "mira"]):
    machname = "theta"
    print("Error! Setting machname to "+str(machname))

# ALCF resource (use COBALT)
if machname in ["theta", "mira"]:
    if not(ccio or romio_col or romio_ind or cray_col or cray_ind):
        print("You didn't provide any settings to test - running ccio.")
        ccio = True
    nodes=int(os.environ['COBALT_JOBSIZE'])
    print("Using "+str(nodes)+" nodes.")
    nranks=nodes*ppn
    #jobid=int(os.environ['COBALT_JOBID'])
    if machname in ["theta"]:
        # Allow module load/swap/list etc:
        execfile(os.environ['MODULESHOME']+'/init/python.py')
        # Load the correct module for cray-mpich:
        module('unload','cray-mpich')
        if mpiversion == "0": mpiversion = "7_7_0"
        mpi_label = mpiversion
        mpi_label_split = mpi_label.split("_")
        mpi_label_dots = mpi_label_split[0]+"."+mpi_label_split[1]+"."+mpi_label_split[2]
        module('load','cray-mpich/'+str(mpi_label_dots))
        #module('load','cray-hdf5-parallel')
        if execname == notset:
            execname = "/home/zamora/hdf5_root_dir/exerciser/build-theta-opt/hdf5Exerciser-theta-opt-ccio"
        if outroot == notset:
            outroot = "/lus-projects/datascience/rzamora/exerciser/ccio-hdf5"
    elif machname in ["mira"]:
        lfs_size = "8m" # This value cannot be changed on BGQ
        if execname == notset:
            execname = "/home/zamora/hdf5_root_dir/exerciser/build-theta-opt/hdf5Exerciser-mira-opt-ccio"
        if outroot == notset:
            outroot = "/projects/datascience/rzamora/exerciser/ccio-hdf5"
# Desktop resource
elif machname in ["mac"]:
    if not(ccio or romio_col or romio_ind):
        print("You didn't provide any settings to test - running romio_col.")
        romio_col = True
    nranks=nodes*ppn
    if execname == notset:
        execname = "/Users/rzamora/IO/CCIO/exerciser/build/hdf5Exerciser-mac-opt"
    if outroot == notset:
        outroot = "./"

# ---------------------------------------------------------------------------- #
#  Create the output directory
# ---------------------------------------------------------------------------- #

rundir = outroot+"/mpi."+mpiversion+".stripecount."+str(lfs_count)+".size."+str(lfs_size)+".nodes."+str(nodes)+".ppn."+str(ppn)
if not os.path.isdir(rundir): subprocess.call(["mkdir",rundir])
os.chdir(rundir)

# ---------------------------------------------------------------------------- #
#  Get a reasonable dimranks, minb, bmult, and nsizes params
# ---------------------------------------------------------------------------- #

dimranks = [nranks]
if dim>4: print("ERROR: >4 dimensions not set up"); dim=4
for i in range(dim-1): dimranks.append(1)
if dim==1:
    if minb == notset: minb = 256
    if bmult == notset: bmult = 8
    if nsizes == notset: nsizes = 4
elif dim==2:
    if minb == notset: minb = 8
    if bmult == notset: bmult = 4
    if nsizes == notset: nsizes = 4
elif dim==3:
    if minb == notset: minb = 8
    if bmult == notset: bmult = 2
    if nsizes == notset: nsizes = 4
elif dim==4:
    if minb == notset: minb = 3
    if bmult == notset: bmult = 2
    if nsizes == notset: nsizes = 4
else: print("ERROR: >4 dimensions not set up"); sys.exit(-1)

# ---------------------------------------------------------------------------- #
#  Execute the desired job -- Steps depend on the machine
# ---------------------------------------------------------------------------- #

# HDF5 Env Defaults
os.environ["HDF5_ASYNC_IO"]="no"
os.environ["HDF5_CUSTOM_AGG_WR"]="no"
os.environ["HDF5_CUSTOM_AGG_RD"]="no"
os.environ["HDF5_CUSTOM_AGG_DEBUG"]="no"
os.environ["HDF5_TOPO_AGG"]="no"

# Machine-specific execution steps:
if machname in ["theta"]:

    # Set lustre stripe properties
    subprocess.call(["lfs","setstripe","-c",str(lfs_count),"-S",str(lfs_size)+"m","."])

    # Define env and part of aprun command that wont change
    #os.environ["MPICH_MPIIO_TIMERS"]="1"
    #os.environ["MPICH_MPIIO_STATS"]="1"
    os.environ["MPICH_MPIIO_AGGREGATOR_PLACEMENT_DISPLAY"]="1"
    os.environ["PMI_LABEL_ERROUT"]="1"
    os.environ["MPICH_MPIIO_CB_ALIGN"]="2"
    os.environ["MPICH_MPIIO_HINTS"]="*:romio_ds_write=disable"
    subprocess.Popen('ulimit -c unlimited', shell=True)
    cmd = ["aprun"]
    cmd.append("-n"); cmd.append(str(nranks)); cmd.append("-N"); cmd.append(str(ppn))
    cmd.append("-d"); cmd.append("1"); cmd.append("-j"); cmd.append("1")
    cmd.append("-cc"); cmd.append("depth"); cmd.append(execname)
    cmd.append("--numdims"); cmd.append(str(dim))
    cmd.append("--minels")
    for i in range(dim): cmd.append(str(minb))
    cmd.append("--bufmult");
    for i in range(dim): cmd.append(str(bmult));
    cmd.append("--nsizes"); cmd.append(str(nsizes))
    cmd.append("--dimranks")
    for i in range(dim): cmd.append(str(dimranks[i]))
    cmd.append("--metacoll"); cmd.append("--addattr"); #cmd.append("--derivedtype")
    if rshift: cmd.append("--rshift"); cmd.append(str(ppn))
    if perf: cmd.append("--perf")
    if debug: os.environ["HDF5_CUSTOM_AGG_DEBUG"]="yes"
    cmd_root=list(cmd)

    with open("results."+os.environ['COBALT_JOBID'], "a") as outf:

        # Run ROMIO Collective I/O
        if romio_col:

            os.environ["MPICH_MPIIO_CB_ALIGN"]="3"
            subprocess.call(["echo","romio two-phase:"], stdout=outf)
            cmd = list(cmd_root)
            subprocess.call(cmd, stdout=outf); print(cmd)

            if topohint:
                os.environ["MPICH_MPIIO_CB_ALIGN"]="3"
                subprocess.call(["echo","romio two-phase-topo:"], stdout=outf)
                cmd = list(cmd_root); cmd.append("--topohint")
                subprocess.call(cmd, stdout=outf); print(cmd)

        # Run ROMIO Independent I/O
        if romio_ind:

            os.environ["MPICH_MPIIO_CB_ALIGN"]="3"
            subprocess.call(["echo","romio indepio:"], stdout=outf)
            cmd = list(cmd_root); cmd.append("--indepio")
            subprocess.call(cmd, stdout=outf); print(cmd)

        # Run CRAY-MPICH Collective I/O
        if cray_col:

            os.environ["MPICH_MPIIO_CB_ALIGN"]="2"
            subprocess.call(["echo","cray-mpi two-phase:"], stdout=outf)
            cmd = list(cmd_root)
            subprocess.call(cmd, stdout=outf); print(cmd)

        # Run CRAY-MPICH Independent I/O
        if cray_ind:

            os.environ["MPICH_MPIIO_CB_ALIGN"]="2"
            subprocess.call(["echo","cray-mpi indepio:"], stdout=outf)
            cmd = list(cmd_root); cmd.append("--indepio")
            subprocess.call(cmd, stdout=outf); print(cmd)

        # Run CCIO
        if ccio:

            # Set number of aggregators if we are overriding the default
            if naggs > 0:
                os.environ["HDF5_CB_NODES_OVERRIDE"]=str(naggs)
                subprocess.call(["echo","HDF5_CB_NODES_OVERRIDE="+str(naggs)], stdout=outf)

            # CCIO With Blocking I/O
            os.environ["MPICH_MPIIO_CB_ALIGN"]="3"
            os.environ["HDF5_CUSTOM_AGG_WR"]="yes"
            os.environ["HDF5_CUSTOM_AGG_RD"]="yes"
            os.environ["HDF5_ASYNC_IO"]="no"
            subprocess.call(["echo","One-sided-blocking:"], stdout=outf)
            cmd = list(cmd_root)
            subprocess.call(cmd, stdout=outf); print(cmd)

            if topology:
                os.environ["HDF5_CUSTOM_TOPO"]="yes"
                subprocess.call(["echo","One-sided-blocking-topo:"], stdout=outf)
                cmd = list(cmd_root)
                subprocess.call(cmd, stdout=outf); print(cmd)

            if async:

                # CCIO With Asynchronous I/O
                os.environ["MPICH_MPIIO_CB_ALIGN"]="3"
                os.environ["HDF5_CUSTOM_AGG_WR"]="yes"
                os.environ["HDF5_CUSTOM_AGG_RD"]="yes"
                os.environ["HDF5_ASYNC_IO"]="yes"
                os.environ["HDF5_TOPO_AGG"]="no"
                subprocess.call(["echo","One-sided-async:"], stdout=outf)
                cmd = list(cmd_root)
                subprocess.call(cmd, stdout=outf); print(cmd)

                if topology:
                    os.environ["HDF5_CUSTOM_TOPO"]="yes"
                    subprocess.call(["echo","One-sided-async-topo:"], stdout=outf)
                    cmd = list(cmd_root)
                    subprocess.call(cmd, stdout=outf); print(cmd)

            # Reset env vars to non-ccio behavior
            os.environ["HDF5_CUSTOM_AGG_WR"]="no"
            os.environ["HDF5_CUSTOM_AGG_RD"]="no"
            os.environ["HDF5_ASYNC_IO"]="no"
            os.environ["HDF5_TOPO_AGG"]="no"

elif machname in ["mira"]:

    # Recall that environment variables are annoying on BGQ
    # (need to pass --envs flafs in 'runjob' command)

    cmd = ["runjob"]
    cmd.append("--np"); cmd.append(str(nranks)); cmd.append("-p"); cmd.append(str(ppn))
    cmd.append("--block"); cmd.append(os.environ['COBALT_PARTNAME'])
    if debug: cmd.append("--envs"); cmd.append("HDF5_CUSTOM_AGG_DEBUG=yes")
    if naggs > 0: cmd.append("--envs"); cmd.append("HDF5_CB_NODES_OVERRIDE="+str(naggs))
    if topohint: cmd.append("--envs"); cmd.append("HDF5_I_DIV=4")
    cmd_root_1=list( cmd )

    cmd = [":"]; cmd.append(execname)
    cmd.append("--numdims"); cmd.append(str(dim))
    cmd.append("--minels")
    for i in range(dim): cmd.append(str(minb))
    cmd.append("--bufmult");
    for i in range(dim): cmd.append(str(bmult));
    cmd.append("--nsizes"); cmd.append(str(nsizes))
    cmd.append("--dimranks")
    for i in range(dim): cmd.append(str(dimranks[i]))
    cmd.append("--metacoll"); cmd.append("--addattr"); #cmd.append("--derivedtype")
    if perf: cmd.append("--perf")
    if rshift: cmd.append("--rshift"); cmd.append(str(ppn))
    cmd_root_2=list( cmd )

    with open("results."+os.environ['COBALT_JOBID'], "a") as outf:

        # Run ROMIO Collective I/O
        if romio_col:

            if not topohint:

                subprocess.call(["echo","romio two-phase:"], stdout=outf)
                cmd = list( cmd_root_1 + cmd_root_2 )
                subprocess.call(cmd, stdout=outf); print(cmd)

            else:
                subprocess.call(["echo","romio two-phase-topo:"], stdout=outf)
                cmd = list(cmd_root_1); cmd.append("--envs"); cmd.append("HDF5_CB_REV=no")
                cmd = list( cmd + cmd_root_2 ); cmd.append("--topohint")
                subprocess.call(cmd, stdout=outf); print(cmd)

                subprocess.call(["echo","romio two-phase-topo-reversed:"], stdout=outf)
                cmd = list(cmd_root_1); cmd.append("--envs"); cmd.append("HDF5_CB_REV=yes")
                cmd = list( cmd + cmd_root_2 ); cmd.append("--topohint")
                subprocess.call(cmd, stdout=outf); print(cmd)

        # Run ROMIO Independent I/O
        if romio_ind:

            subprocess.call(["echo","romio indepio:"], stdout=outf)
            cmd = list( cmd_root_1 + cmd_root_2 ); cmd.append("--indepio")
            subprocess.call(cmd, stdout=outf); print(cmd)

        # Run CCIO
        if ccio:

            # Set number of aggregators if we are overriding the default
            if naggs > 0:
                os.environ["HDF5_CB_NODES_OVERRIDE"]=str(naggs)
                subprocess.call(["echo","HDF5_CB_NODES_OVERRIDE="+str(naggs)], stdout=outf)

            # CCIO With Blocking I/O
            os.environ["HDF5_CUSTOM_AGG_WR"]="yes"
            os.environ["HDF5_CUSTOM_AGG_RD"]="yes"
            os.environ["HDF5_ASYNC_IO"]="no"
            subprocess.call(["echo","One-sided-blocking:"], stdout=outf)
            cmd = list(cmd_root_1); cmd.append( cmd_root_2[:] )
            subprocess.call(cmd, stdout=outf); print(cmd)

            if topology:
                os.environ["HDF5_CUSTOM_TOPO"]="yes"
                subprocess.call(["echo","One-sided-blocking-topo:"], stdout=outf)
                cmd = list( cmd_root_1 + cmd_root_2 )
                subprocess.call(cmd, stdout=outf); print(cmd)

            if async:

                # CCIO With Asynchronous I/O
                os.environ["HDF5_CUSTOM_AGG_WR"]="yes"
                os.environ["HDF5_CUSTOM_AGG_RD"]="yes"
                os.environ["HDF5_ASYNC_IO"]="yes"
                os.environ["HDF5_TOPO_AGG"]="no"
                subprocess.call(["echo","One-sided-async:"], stdout=outf)
                cmd = list( cmd_root_1 + cmd_root_2 )
                subprocess.call(cmd, stdout=outf); print(cmd)

                if topology:
                    os.environ["HDF5_CUSTOM_TOPO"]="yes"
                    subprocess.call(["echo","One-sided-async-topo:"], stdout=outf)
                    cmd = list( cmd_root_1 + cmd_root_2 )
                    subprocess.call(cmd, stdout=outf); print(cmd)

            # Reset env vars to non-ccio behavior
            os.environ["HDF5_CUSTOM_AGG_WR"]="no"
            os.environ["HDF5_CUSTOM_AGG_RD"]="no"
            os.environ["HDF5_ASYNC_IO"]="no"
            os.environ["HDF5_TOPO_AGG"]="no"

elif machname in ["mac"]:

    cmd = ["mpirun"]
    cmd.append("-n"); cmd.append(str(nranks))
    cmd.append(execname)
    cmd.append("--numdims"); cmd.append(str(dim))
    cmd.append("--minels")
    for i in range(dim): cmd.append(str(minb))
    cmd.append("--bufmult");
    for i in range(dim): cmd.append(str(bmult));
    cmd.append("--nsizes"); cmd.append(str(nsizes))
    cmd.append("--dimranks")
    for i in range(dim): cmd.append(str(dimranks[i]))
    cmd.append("--metacoll"); cmd.append("--addattr");
    if rshift: cmd.append("--rshift"); cmd.append(str(ppn))
    cmd_root=list(cmd)

    # Run ROMIO Collective I/O
    if romio_col:

        with open("results.0", "a") as outf:

            subprocess.call(["echo","romio two-phase:"], stdout=outf, stderr=outf)
            cmd = list(cmd_root)
            subprocess.call(cmd, stdout=outf, stderr=outf); print(cmd)

            if topohint:
                subprocess.call(["echo","romio two-phase-topo:"], stdout=outf, stderr=outf)
                cmd = list(cmd_root); cmd.append("--topohint")
                subprocess.call(cmd, stdout=outf, stderr=outf); print(cmd)

    # Run ROMIO Independent I/O
    if romio_ind:

        with open("results.0", "a") as outf:

            subprocess.call(["echo","romio indepio:"], stdout=outf, stderr=outf)
            cmd = list(cmd_root); cmd.append("--indepio")
            subprocess.call(cmd, stdout=outf, stderr=outf); print(cmd)


# ---------------------------------------------------------------------------- #
#  Done.
# ---------------------------------------------------------------------------- #

cmd = ["echo","done"]
subprocess.call(cmd)
