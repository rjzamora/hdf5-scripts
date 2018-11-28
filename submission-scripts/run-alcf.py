#!/usr/bin/env python
#COBALT -A datascience
#COBALT -n 128
#COBALT -t 30

machine   = "mac"

if machine == "theta":
    lfs_count = 48
    lfs_size  = 8
    ppn       = 32
    cb_mult   = 1
    cb_div    = 1
    dim       = 3
    minb      = 16
    bmult     = 2
    nsizes    = 3
    dimranks  = [ 16, 16, 16 ]
    rshift    = True
else:
    lfs_count = 4
    lfs_size  = 1
    ppn       = 8
    pps       = 2
    cb_mult   = 1
    cb_div    = 1
    dim       = 3
    minb      = 32
    bmult     = 2
    nsizes    = 3
    dimranks  = [ 4, 2, 2 ]
    rshift    = True

# Load python modules
import subprocess
import os

# Env vars that we wont change here:
envs_const = [ ]
if machine == "mac":
    nodes      = 1
else:
    nodes      = int(os.environ['COBALT_JOBSIZE'])
nranks     = ppn * nodes
cb_nodes   = (lfs_count * cb_mult) / cb_div
cb_stride  = (nranks) / cb_nodes
fsb_size   = lfs_size * (1024 * 1024)
fsb_count  = lfs_count
pwdroot    = os.environ['PWD']

if machine == "theta":
    # Allow module load/swap/list etc:
    execfile(os.environ['MODULESHOME']+'/init/python.py')
    os.environ['MPICH_MPIIO_HINTS'] = '*:cray_cb_write_lock_mode=1'
    os.environ['MPICH_NEMESIS_ASYNC_PROGRESS'] = 'ML'
    os.environ['MPICH_MAX_THREAD_SAFETY'] = 'multiple'
    module('unload','darshan')
    execname  = "/home/zamora/hdf5_root_dir/exerciser/build-theta-g-ccio/hdf5Exerciser-theta-g-ccio"

elif machine == "vesta":
    envs_const.append("BGLOCKLESSMPIO_F_TYPE=0x47504653")
    execname  = "/home/zamora/hdf5_root_dir/exerciser/build-opt-g-ccio/hdf5Exerciser-opt-g-ccio"

else:
    if ppn>0: os.environ['HDF5_CCIO_TOPO_PPN'] = str(ppn)
    if pps>0: os.environ['HDF5_CCIO_TOPO_PPS'] = str(pps)
    execname  = pwdroot+"/hdf5Exerciser-mac-mpich"

def export_envs( envs_dyn ):

    for env in envs_dyn:
        env_split  = env.split("=")
        env_name   = env_split[0]
        env_value  = env_split[1]
        subprocess.call(["echo","Setting "+env_name+" to "+env_value+"."], stdout=outf)
        os.environ[ env_name ] = env_value

def get_runjob_cmd( envs_dyn ):

    if machine == "vesta":

        cmd = ["runjob"]
        cmd.append("--np");    cmd.append(str(nranks))
        cmd.append("-p");      cmd.append(str(ppn))
        cmd.append("--block"); cmd.append(os.environ['COBALT_PARTNAME'])

        # Environment variables added here
        for env in envs_const:
            cmd.append("--envs");  cmd.append(env)
        for env in envs_dyn:
            cmd.append("--envs");  cmd.append(env)

        # Exerciser args
        cmd.append(":"); cmd.append(execname)
        cmd.append("--numdims"); cmd.append(str(dim))
        cmd.append("--minels")
        for i in range(dim): cmd.append(str(minb))
        cmd.append("--bufmult");
        for i in range(dim): cmd.append(str(bmult));
        cmd.append("--nsizes"); cmd.append(str(nsizes))
        if not (dimranks==None):
            cmd.append("--dimranks")
            for i in range(dim): cmd.append(str(dimranks[i]))
        #cmd.append("--metacoll"); cmd.append("--addattr"); cmd.append("--derivedtype")
        if rshift: cmd.append("--rshift"); cmd.append(str(ppn))

    elif machine == "theta":

        export_envs( envs )
        # Define env and part of aprun command that wont change
        #os.environ["MPICH_MPIIO_TIMERS"]="1"
        #os.environ["MPICH_MPIIO_STATS"]="1"
        os.environ["MPICH_MPIIO_AGGREGATOR_PLACEMENT_DISPLAY"]="1"
        os.environ["PMI_LABEL_ERROUT"]="1"
        os.environ["MPICH_MPIIO_CB_ALIGN"]="2"
        #os.environ["MPICH_MPIIO_HINTS"]="*:romio_ds_write=disable"
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
        #cmd.append("--metacoll"); cmd.append("--addattr"); cmd.append("--derivedtype")
        if rshift: cmd.append("--rshift"); cmd.append(str(ppn))

    else:

        export_envs( envs )
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
        #cmd.append("--metacoll"); cmd.append("--addattr"); cmd.append("--derivedtype")
        if rshift: cmd.append("--rshift"); cmd.append(str(ppn))

    return cmd

rundir = pwdroot+"/stripecount."+str(lfs_count)+".size."+str(lfs_size)+".nodes."+str(nodes)+".ppn."+str(ppn)
if not os.path.isdir(rundir): subprocess.call(["mkdir",rundir])
os.chdir(rundir)
if machine == "mac":
    jobid_i = 0
    while os.path.isdir( rundir+"/results."+str(jobid_i) ):
        jobid_i += 1
    jobid = str(jobid_i)
else: jobid = os.environ['COBALT_JOBID']
with open("results."+jobid, "a") as outf:

    if machine == "theta":
        # Set lustre stripe properties
        subprocess.call(["lfs","setstripe","-c",str(lfs_count),"-S",str(lfs_size)+"m","."])

    # Blocking CCIO
    subprocess.call(["echo",""], stdout=outf)
    subprocess.call(["echo","[EXPERIMENT] [0] [Blocking-CCIO]:"], stdout=outf)
    envs = [
    "HDF5_CCIO_CB_SIZE="+str(fsb_size),
    "HDF5_CCIO_FS_BLOCK_SIZE="+str(fsb_size),
    "HDF5_CCIO_FS_BLOCK_COUNT="+str(fsb_count),
    "HDF5_CCIO_DEBUG=no",
    "HDF5_CCIO_WR_METHOD=2", "HDF5_CCIO_RD_METHOD=2",
    "HDF5_CCIO_WR=yes", "HDF5_CCIO_RD=yes", "HDF5_CCIO_ASYNC=no",
    "HDF5_CCIO_CB_NODES="+str(cb_nodes), "HDF5_CCIO_CB_STRIDE=0",
    "HDF5_CCIO_TOPO_CB_SELECT=no"
    ]
    cmd = list( get_runjob_cmd( envs ) ); print(cmd)
    subprocess.call(cmd, stdout=outf)


    # Pipe-lined CCIO
    subprocess.call(["echo",""], stdout=outf)
    subprocess.call(["echo","[EXPERIMENT] [1] [Pipelined-CCIO]:"], stdout=outf)
    envs = [
    "HDF5_CCIO_CB_SIZE="+str(fsb_size),
    "HDF5_CCIO_FS_BLOCK_SIZE="+str(fsb_size),
    "HDF5_CCIO_FS_BLOCK_COUNT="+str(fsb_count),
    "HDF5_CCIO_DEBUG=no",
    "HDF5_CCIO_WR_METHOD=2", "HDF5_CCIO_RD_METHOD=2",
    "HDF5_CCIO_WR=yes", "HDF5_CCIO_RD=yes", "HDF5_CCIO_ASYNC=yes",
    "HDF5_CCIO_CB_NODES="+str(cb_nodes), "HDF5_CCIO_CB_STRIDE=0",
    "HDF5_CCIO_TOPO_CB_SELECT=no"
    ]
    cmd = list( get_runjob_cmd( envs ) ); print(cmd)
    subprocess.call(cmd, stdout=outf);


    # Topology-aware CCIO
    subprocess.call(["echo",""], stdout=outf)
    subprocess.call(["echo","[EXPERIMENT] [2] [Topology-Aware-CCIO]:"], stdout=outf)
    envs = [
    "HDF5_CCIO_CB_SIZE="+str(fsb_size),
    "HDF5_CCIO_FS_BLOCK_SIZE="+str(fsb_size),
    "HDF5_CCIO_FS_BLOCK_COUNT="+str(fsb_count),
    "HDF5_CCIO_DEBUG=no",
    "HDF5_CCIO_WR_METHOD=2", "HDF5_CCIO_RD_METHOD=2",
    "HDF5_CCIO_WR=yes", "HDF5_CCIO_RD=yes", "HDF5_CCIO_ASYNC=yes",
    "HDF5_CCIO_CB_NODES="+str(cb_nodes), "HDF5_CCIO_CB_STRIDE=0",
    "HDF5_CCIO_TOPO_CB_SELECT=yes"
    ]
    cmd = list( get_runjob_cmd( envs ) ); print(cmd)
    subprocess.call(cmd, stdout=outf);


    subprocess.call(["echo",""], stdout=outf)
    subprocess.call(["echo","[EXPERIMENT] [3] [Bad-Agg-CCIO]:"], stdout=outf)
    envs = [
    "HDF5_CCIO_CB_SIZE="+str(fsb_size),
    "HDF5_CCIO_FS_BLOCK_SIZE="+str(fsb_size),
    "HDF5_CCIO_FS_BLOCK_COUNT="+str(fsb_count),
    "HDF5_CCIO_DEBUG=no",
    "HDF5_CCIO_WR_METHOD=2", "HDF5_CCIO_RD_METHOD=2",
    "HDF5_CCIO_WR=yes", "HDF5_CCIO_RD=yes", "HDF5_CCIO_ASYNC=yes",
    "HDF5_CCIO_CB_NODES="+str(cb_nodes), "HDF5_CCIO_CB_STRIDE=1",
    "HDF5_CCIO_TOPO_CB_SELECT=no"
    ]
    cmd = list( get_runjob_cmd( envs ) ); print(cmd)
    subprocess.call(cmd, stdout=outf);


    subprocess.call(["echo",""], stdout=outf)
    subprocess.call(["echo","[EXPERIMENT] [4] [Default-Collective]:"], stdout=outf)
    envs = [
    "HDF5_CCIO_WR=no", "HDF5_CCIO_RD=no",
    ]
    cmd = list( get_runjob_cmd( envs ) ); print(cmd)
    subprocess.call(cmd, stdout=outf);


    subprocess.call(["echo",""], stdout=outf)
    subprocess.call(["echo","[EXPERIMENT] [5] [Default-Independent]:"], stdout=outf)
    cmd = list( get_runjob_cmd( envs ) ); cmd.append("--indepio"); print(cmd)
    subprocess.call(cmd, stdout=outf);

# ---------------------------------------------------------------------------- #
#  Done.
# ---------------------------------------------------------------------------- #

cmd = ["echo","done"]
subprocess.call(cmd)
