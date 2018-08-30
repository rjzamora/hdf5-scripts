import subprocess
import os.path
import sys
import glob
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import pylab
import numpy as np
import math

KB = 1024
MB = 1048576
GB = 1073741824

plt.style.use('ggplot')
dirs = glob.glob('mpi.*.stripecount.*')

machine = 'theta'
plots = [\
{ 'ops': ['romio-2-phase', 'romio-2-phase-topo'], 'dim': 3 }
]

lustre_settings = [ [16, 1] ] # [count, size]

globalList = []
for dir in dirs:

    di = {}

    print(dir)
    splitname = dir.split('.')
    mpiversion = splitname[1]
    count = int(splitname[3])
    size = int(splitname[5])
    nodes = int(splitname[7])
    ppn = int(splitname[9])
    if not ([count, size] in lustre_settings):
        print('No lustre settings to plot!!')
        continue
    di['mpi'] = mpiversion
    di['machine'] = machine
    di['count'] = count
    di['size'] = size
    di['nodes'] = nodes
    di['ppn'] = ppn

    files = glob.glob(dir+'/results.*')

    for filei in files:

        with open(filei, 'r') as f:
            d = di
            labels = []
            ilbl=0
            while True:
                line = f.readline()
                if not line: break
                fsplt = line.split()
                if len(fsplt)>0:

                    if fsplt[0]=='One-sided:':
                        d[ 'optype' ] = 'One-sided'

                    elif (fsplt[0]=='romio' and fsplt[1]=='two-phase:'):
                        d[ 'optype' ] = 'romio-2-phase'
                    elif (fsplt[0]=='romio' and fsplt[1]=='indepio:'):
                        d[ 'optype' ] = 'romio-independent'
                    elif (fsplt[0]=='romio' and fsplt[1]=='two-phase-topo:'):
                        d[ 'optype' ] = 'romio-2-phase-topo'

                    elif (fsplt[0]=='cray-mpi' and fsplt[1]=='two-phase:'):
                        d[ 'optype' ] = 'cray-mpi-2-phase'
                    elif (fsplt[0]=='cray-mpi' and fsplt[1]=='indepio:'):
                        d[ 'optype' ] = 'cray-mpi-independent'
                    elif (fsplt[0]=='cray-mpi' and fsplt[1]=='two-phase' and fsplt[2]=='chunked:'):
                        d[ 'optype' ] = 'cray-mpi-2-phase-chunked'
                    elif (fsplt[0]=='cray-mpi' and fsplt[1]=='indepio' and fsplt[2]=='chunked:'):
                        d[ 'optype' ] = 'cray-mpi-independent-chunked'

                    elif (len(fsplt)>1) and (fsplt[0]=='0:'):
                        # 0/1 Options
                        if fsplt[1]=='useMetaDataCollectives:':
                            for j in range(1,len(fsplt), 2): d[ fsplt[j] ] = int( fsplt[j+1] )
                        # Columns labels
                        elif fsplt[1]=='Metric':
                            labels.append( fsplt[2]) #BufSize
                            for j in range(3,len(fsplt)): labels.append( fsplt[j]+'-Min' )
                            for j in range(3,len(fsplt)): labels.append( fsplt[j]+'-Med' )
                            for j in range(3,len(fsplt)): labels.append( fsplt[j]+'-Max' )
                            for j in range(3,len(fsplt)): labels.append( fsplt[j]+'-Avg' )
                            for j in range(3,len(fsplt)): labels.append( fsplt[j]+'-Std' )
                        # Table Values
                        elif (fsplt[1]=='Min'):

                            ilbl=0
                            d[ labels[ilbl] ] = int( fsplt[2] ) #BufSize
                            for j in range(3,len(fsplt)):
                                ilbl+=1
                                d[ labels[ilbl] ] = float( fsplt[j] )

                        elif (fsplt[1]=='Med') or (fsplt[1]=='Max') or (fsplt[1]=='Avg'):

                            for j in range(3,len(fsplt)):
                                ilbl+=1
                                d[ labels[ilbl] ] = float( fsplt[j] )

                        elif (fsplt[1]=='Std'):

                            for j in range(3,len(fsplt)):
                                ilbl+=1
                                d[ labels[ilbl] ] = float( fsplt[j] )

                            # Append dictionary to global list
                            globalList.append({})
                            for key in d: globalList[-1][key] = d[key]

                            # Replace data that is already 'written'
                            for label in labels: d[ label ] = None

df = pd.DataFrame.from_dict(globalList)
#print(df)
##df.to_csv('organized_data.csv')
#sys.exit(0)

df_grp = df.groupby(['machine','optype','numDims:','mpi','Bufsize','count','size']).mean().reset_index()
groups = df_grp.groupby(['machine','optype','numDims:','mpi','count','size'])

for looptype in plots:

    allowed_ops = looptype['ops'] # List of allowed mpi types
    allowed_dim = looptype['dim']

    f3, ax3 = plt.subplots(1, 2, figsize=(12, 6))

    colorch=['k','b','g','r','c','m','k','b','g','r','c','m',];cind=0;
    numdims=1

    icnt=0
    for mname,machgrp in groups:

        if not (mname[1] in allowed_ops): continue
        if not (mname[2] == allowed_dim): continue
        numdims = mname[2]

        Bufsize = machgrp['Bufsize'].tolist()
        H5DWrite = machgrp['H5DWrite-Avg'].tolist()
        H5Dread = machgrp['H5Dread-Avg'].tolist()
        H5Fopen = machgrp['H5Fopen-Avg'].tolist()
        H5Fflush = machgrp['H5Fflush-Avg'].tolist()
        H5DWrite_Std = machgrp['H5DWrite-Std'].tolist()
        H5Dread_Std = machgrp['H5Dread-Std'].tolist()
        H5Fopen_Std = machgrp['H5Fopen-Std'].tolist()
        H5Fflush_Std = machgrp['H5Fflush-Std'].tolist()

        RawWrBDWTH = machgrp['RawWrBDWTH-Avg'].tolist()
        RawRdBDWTH = machgrp['RawRdBDWTH-Avg'].tolist()
        RawWrBDWTH_Std = machgrp['RawWrBDWTH-Std'].tolist()
        RawRdBDWTH_Std = machgrp['RawRdBDWTH-Std'].tolist()
        RawWrBDWTH_Med = machgrp['RawWrBDWTH-Med'].tolist()
        RawRdBDWTH_Med = machgrp['RawRdBDWTH-Med'].tolist()
        RawWrBDWTH_Min = machgrp['RawWrBDWTH-Min'].tolist()
        RawRdBDWTH_Min = machgrp['RawRdBDWTH-Min'].tolist()
        RawWrBDWTH_Max = machgrp['RawWrBDWTH-Max'].tolist()
        RawRdBDWTH_Max = machgrp['RawRdBDWTH-Max'].tolist()

        for i in range(len(Bufsize)): Bufsize[i] = Bufsize[i] / 1024.0

        #strlbl = str(mname[0])+" - "+str( mname[1] )+" - mpi-"+str( mname[3] )
        str_use = str( mname[1] )
        if(str_use == 'cray-mpi-2-phase'): str_use = 'Collective I/O'
        if(str_use == 'cray-mpi-independent'): str_use = 'Independent I/O'
        if(str_use == 'One-sided'): str_use = 'One-sided Collective I/O'
        strlbl = str_use+" - stripe_size: "+str( mname[5] )+" - stripe_count: "+str( mname[4] )
        ind = np.arange(len(H5DWrite))
        width=0.03

        itemupRd=[];itemdnRd=[]
        itemupWr=[];itemdnWr=[]
        for it in range(len(RawWrBDWTH_Med)):
            itdn = RawWrBDWTH_Med[it]-RawWrBDWTH_Min[it]; itemdnWr.append(itdn)
            itup = RawWrBDWTH_Max[it]-RawWrBDWTH_Med[it]; itemupWr.append(itup)
            itdn = RawRdBDWTH_Med[it]-RawRdBDWTH_Min[it]; itemdnRd.append(itdn)
            itup = RawRdBDWTH_Max[it]-RawRdBDWTH_Med[it]; itemupRd.append(itup)

        if str_use == 'One-sided Collective I/O': ucol = 'b'
        else: ucol = 'k'
        ucol = colorch[cind]

        if mname[4] == 1:
            ufmt = '_:'; ulw = 1
        elif mname[4] == 8:
            ufmt = '_--'; ulw = 1
        else:
            ufmt = '_-'; ulw = 1.5

        ax3[0].errorbar(ind+width*icnt, RawWrBDWTH_Med, yerr=[itemdnWr, itemupWr], fmt='none', ecolor=ucol, lw=ulw)
        ax3[0].errorbar(ind+width*icnt, RawWrBDWTH_Med, yerr=[itemdnWr, itemupWr], fmt=ufmt+ucol, label=strlbl, lw=ulw)
        ax3[1].errorbar(ind+width*icnt, RawRdBDWTH_Med, yerr=[itemdnRd, itemupRd], fmt='none', ecolor=ucol, lw=ulw)
        ax3[1].errorbar(ind+width*icnt, RawRdBDWTH_Med, yerr=[itemdnRd, itemupRd], fmt=ufmt+ucol, label=strlbl, lw=ulw)
        cind+=1
        icnt+=1

    if icnt == 0: continue

    ticklabels = []
    for item in Bufsize:
        if item >= 1.0: val = int(item)
        else: val = item
        ticklabels.append(str(val)+'KiB')

    f3.text(0.5, 0.925, str(numdims)+'D Dataset HDF5 Performance on Theta/Lustre \n( '+str(nodes*ppn)+' Processes, ppn='+str(ppn)+' )',horizontalalignment='center',color='black',weight='bold',size='large')

    ax3[0].set_title('H5Dwrite'); ax3[0].set_ylabel('Bandwidth [MiB/sec]')
    ax3[1].set_title('H5Dread'); ax3[1].set_ylabel('Bandwidth [MiB/sec]')

    for i in range(2):
        ax3[i].set_xlabel('Local Buffer Size')
        ifact = cind/2.0-0.5
        ax3[i].set_xticks(ind+width*ifact); ax3[i].set_xticklabels(ticklabels)
        ax3[i].set_yscale('log')
    ax3[0].legend(loc=9, bbox_to_anchor=(1.1, -0.15), ncol=2, shadow=True)
    plt.subplots_adjust(left=0.08, bottom=0.24, right=0.96, top=None, wspace=None, hspace=None)

    # Name the figure appropriately
    namestr = 'mpi_'+mpiversion;
    for opstr in allowed_ops:
        namestr = namestr+'_'+opstr
    filename = namestr+'_'+str(numdims)+'d_count'+str(count)+'_size'+str(size)+'mb_nodes'+str(nodes)+'_ppn'+str(ppn)
    f3.savefig(filename, dpi=100)

plt.show()
