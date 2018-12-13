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

#plt.style.use('ggplot')
dirs = glob.glob('stripecount.*')
nodecnt = 512
orient = 0 # 0 == vertical, 1 == horizontal

machine = 'vesta'
naggs   = 32
plots = [\
{ 'ops': ['blocking-ccio',
          'topology-aware-ccio-data',
          'topology-aware-ccio-spread',
          'topology-aware-ccio-random',
          'topology-aware-ccio-1st-ranks',
          'topology-aware-ccio-1st-nodes'],
  'dim': 1, 'nodes': [ nodecnt ], 'ppn': [ ] },
]

# Choose Metrics to plot (together in each plot)
#   Note: Maximum of two Metrics in list
Metric_types = ['RawWrBDWTH','RawRdBDWTH']
#Metric_types = ['H5DWrite','H5Dread']
#Metric_types = ['H5DWrite','H5Fflush']
#Metric_types = ['H5Dread','H5Fopen']

lustre_settings = [ [16, 8], [32, 8], [128, 8] ] # [count, size]
label_stripe_count = False
label_stripe_size = False

globalList = []
for dir in dirs:

    di = {}

    print(dir)
    splitname = dir.split('.')
    count = int(splitname[1])
    size = int(splitname[3])
    nodes = int(splitname[5])
    ppn = int(splitname[7])
    if not ([count, size] in lustre_settings):
        print('No lustre settings to plot!!')
        continue
    di['machine'] = machine
    di['count'] = count
    di['size'] = size
    di['nodes'] = nodes
    di['ppn'] = ppn
    di['optype'] = 'undefined'
    di['mpi'] = 'undefined'
    dstrt = 0
    if machine == 'theta':
        dstrt = 1

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

                    if fsplt[0]=='[EXPERIMENT]':
                        if fsplt[2]=='[Blocking-CCIO]:':
                            d[ 'optype' ] = 'blocking-ccio'
                        elif fsplt[2]=='[Pipelined-CCIO]:':
                            d[ 'optype' ] = 'pipelined-ccio'
                        elif fsplt[2]=='[Topology-Aware-CCIO-Data]:':
                            d[ 'optype' ] = 'topology-aware-ccio-data'
                        elif fsplt[2]=='[Topology-Aware-CCIO-Spread]:':
                            d[ 'optype' ] = 'topology-aware-ccio-spread'
                        elif fsplt[2]=='[Topology-Aware-CCIO-Random]:':
                            d[ 'optype' ] = 'topology-aware-ccio-random'
                        elif fsplt[2]=='[Topology-Aware-CCIO-First-Ranks]:':
                            d[ 'optype' ] = 'topology-aware-ccio-1st-ranks'
                        elif fsplt[2]=='[Topology-Aware-CCIO-First-Nodes]:':
                            d[ 'optype' ] = 'topology-aware-ccio-1st-nodes'
                        elif fsplt[2]=='[Default-Collective]:':
                            d[ 'optype' ] = 'default-collective'
                        elif fsplt[2]=='[Default-Independent]:':
                            d[ 'optype' ] = 'default-independent'

                    elif len(fsplt)>dstrt:
                        # 0/1 Options
                        if fsplt[dstrt]=='useMetaDataCollectives:':
                            for j in range(dstrt,len(fsplt)-dstrt, 2): d[ fsplt[j] ] = int( fsplt[j+1] )
                        # Columns labels
                        elif fsplt[dstrt]=='Metric':
                            labels.append( fsplt[dstrt+1]) #BufSize
                            for j in range(dstrt+2,len(fsplt)): labels.append( fsplt[j]+'-Min' )
                            for j in range(dstrt+2,len(fsplt)): labels.append( fsplt[j]+'-Med' )
                            for j in range(dstrt+2,len(fsplt)): labels.append( fsplt[j]+'-Max' )
                            for j in range(dstrt+2,len(fsplt)): labels.append( fsplt[j]+'-Avg' )
                            for j in range(dstrt+2,len(fsplt)): labels.append( fsplt[j]+'-Std' )
                        # Table Values
                        elif (fsplt[dstrt]=='Min'):
                            ilbl=0
                            d[ labels[ilbl] ] = int( fsplt[dstrt+1] ) #BufSize
                            for j in range(dstrt+2,len(fsplt)):
                                ilbl+=1
                                d[ labels[ilbl] ] = float( fsplt[j] )
                        elif (fsplt[dstrt]=='Med') or (fsplt[dstrt]=='Max') or (fsplt[dstrt]=='Avg'):
                            for j in range(dstrt+2,len(fsplt)):
                                ilbl+=1
                                d[ labels[ilbl] ] = float( fsplt[j] )
                        elif (fsplt[dstrt]=='Std'):
                            for j in range(dstrt+2,len(fsplt)):
                                ilbl+=1
                                d[ labels[ilbl] ] = float( fsplt[j] )
                            # Append dictionary to global list
                            globalList.append({})
                            for key in d: globalList[-1][key] = d[key]
                            # Replace data that is already 'written'
                            for label in labels: d[ label ] = None

df = pd.DataFrame.from_dict(globalList)
#print(df)
#df.to_csv('organized_data.csv')
#sys.exit(0)

num_metrics = len(Metric_types)
if num_metrics>2:
    num_metrics = 2
    Metric_types = Metric_types[0:2]
org_list = ['Bufsize','machine','optype','numDims:','count','size','nodes','ppn']
mnind = {}; ind = None
for item in org_list:
    mnind[ item ] = ind
    if ind == None: ind = 0
    else: ind += 1

df_grp = df.groupby(org_list).mean().reset_index()
groups = df_grp.groupby(org_list[1:]) # Leave out 'Bufsize'

for looptype in plots:

    allowed_ops = looptype['ops'] # List of allowed mpi types
    allowed_dim = looptype['dim']
    allowed_nds = looptype['nodes']
    allowed_ppn = looptype['ppn']

    if orient == 0:
        f3, ax3 = plt.subplots(num_metrics, 1, figsize=(6, 5*num_metrics))
    else:
        f3, ax3 = plt.subplots(1, num_metrics, figsize=(6.5*num_metrics, 6))
    if num_metrics<2: ax3 = [ ax3 ]

    colorch=['k','b','g','r','c','m','k','b','g','r','c','m',];cind=0;
    numdims=1

    icnt=0
    for mname,machgrp in groups:

        if not (mname[ mnind[ 'optype' ] ] in allowed_ops): continue
        if not (mname[ mnind[ 'numDims:' ] ] == allowed_dim): continue
        if len(allowed_nds) > 0:
            if not (mname[ mnind[ 'nodes' ] ] in allowed_nds): continue
        if len(allowed_ppn) > 0:
            if not (mname[ mnind[ 'ppn' ] ] in allowed_ppn): continue
        numdims = mname[ mnind[ 'numDims:' ] ]
        nodes = mname[ mnind[ 'nodes' ] ]
        ppn = mname[ mnind[ 'ppn' ] ]

        Bufsize = machgrp['Bufsize'].tolist()

        Metrics = []; mind=0 # List of 2 dictionaries (with dict items being data lists)
        for mtype in Metric_types:
            if mind>1: continue # Ignoring all but first 2 metrics
            Metrics.append({})
            Metrics[ mind ][ 'type' ] = mtype
            Metrics[ mind ][ 'Avg' ] = machgrp[ mtype+'-Avg' ].tolist()
            Metrics[ mind ][ 'Std' ] = machgrp[ mtype+'-Std' ].tolist()
            Metrics[ mind ][ 'Med' ] = machgrp[ mtype+'-Med' ].tolist()
            Metrics[ mind ][ 'Min' ] = machgrp[ mtype+'-Min' ].tolist()
            Metrics[ mind ][ 'Max' ] = machgrp[ mtype+'-Max' ].tolist()
            mind+=1

        # Change 'bufsize' units
        for i in range(len(Bufsize)): Bufsize[i] = Bufsize[i] / 1024.0

        # Use general formatting
        ucol = colorch[cind]
        ufmt = 's-'; ulw = 1.
        use_hollow = False
        str_use = str( mname[mnind['optype']] )
        if(str_use == 'default-collective'):
            str_use = 'Default Collective I/O'
            ucol = 'k'
            ufmt = 's--'
        if(str_use == 'default-independent'):
            str_use = 'Default Independent I/O'
            ucol = 'k'
            ufmt = 'o--'
        if(str_use == 'pipelined-ccio'):
            str_use = 'Pipelined CCIO'
            ucol = 'g'
        if(str_use == 'blocking-ccio'):
            str_use = 'Strided'
            ucol = 'k'
        if(str_use == 'topology-aware-ccio-data'):
            str_use = 'Data-aware'
            ucol = 'b'
        if(str_use == 'topology-aware-ccio-spread'):
            str_use = 'Spread'
            ucol = 'g'
        if(str_use == 'topology-aware-ccio-random'):
            str_use = 'Random'
            ucol = 'c'
            ufmt = 's--'
            use_hollow = True
        if(str_use == 'topology-aware-ccio-1st-ranks'):
            str_use = 'First N Ranks'
            ucol = 'r'
        if(str_use == 'topology-aware-ccio-1st-nodes'):
            str_use = 'First N Nodes'
            ucol = 'm'
        strlbl = str_use
        if label_stripe_count:
            strlbl = strlbl+" - stripe_count: "+str( mname[mnind['count']] )
        if label_stripe_size:
            strlbl = strlbl+" - stripe_size: "+str( mname[mnind['size']] )
        width=0.03

        # Generate actual plots...
        ind = np.arange(len( Metrics[0][ 'Avg' ] ))
        pind = 0
        for dict in Metrics:
            itemup=[];itemdn=[]
            for it in range(len( dict[ 'Med' ] )):
                itdn = dict['Avg'][it]-dict['Min'][it]; itemdn.append(itdn)
                itup = dict['Max'][it]-dict['Avg'][it]; itemup.append(itup)
            #ax3[pind].errorbar(ind+width*icnt, dict['Avg'], yerr=[itemdn, itemup], fmt='none', ecolor=ucol, lw=ulw)
            if use_hollow:
                ax3[pind].errorbar(ind+width*icnt, dict['Avg'], yerr=[itemdn, itemup], fmt=ufmt+ucol, label=strlbl, lw=ulw, capsize=5, markerfacecolor='white')
            else:
                ax3[pind].errorbar(ind+width*icnt, dict['Avg'], yerr=[itemdn, itemup], fmt=ufmt+ucol, label=strlbl, lw=ulw, capsize=5)
            if dict['type']=='RawWrBDWTH' or dict['type']=='RawRdBDWTH':
                if num_metrics>1:
                    if dict['type']=='RawWrBDWTH':
                        ax3[pind].set_title('Raw H5DWrite')
                    else:
                        ax3[pind].set_title('Raw H5Dread')
                ax3[pind].set_ylabel('Bandwidth [MiB/sec]')
            else:
                if num_metrics>1: ax3[pind].set_title(dict['type'])
                ax3[pind].set_ylabel('Time [sec]')
            pind += 1
        cind+=1
        icnt+=1

    if icnt == 0: continue

    ticklabels = []
    for item in Bufsize:
        if item >= 1.0: val = int(item)
        else: val = item
        ticklabels.append(str(val)+'KiB')
    if num_metrics<2:
        metric_str = Metric_types[0]
        if metric_str=='RawWrBDWTH': metric_str = 'Raw H5DWrite'
        if metric_str=='RawRdBDWTH': metric_str = 'Raw H5Dread'
        f3.text(0.5, 0.925, str(numdims)+'D Dataset '+metric_str+' Performance - '+str(naggs)+' Aggregators\n( '+str(nodes*ppn)+' Processes, ppn='+str(ppn)+' )',horizontalalignment='center',color='black',weight='bold',size='large')
    else:
        if orient == 0:
            f3.text(0.5, 0.95, str(numdims)+'D Dataset Performance - '+str(naggs)+' Aggregators\n( '+str(nodes*ppn)+' Processes, ppn='+str(ppn)+' )',horizontalalignment='center',color='black',weight='bold',size='large')
        else:
            f3.text(0.5, 0.925, str(numdims)+'D Dataset Performance - '+str(naggs)+' Aggregators\n( '+str(nodes*ppn)+' Processes, ppn='+str(ppn)+' )',horizontalalignment='center',color='black',weight='bold',size='large')

    for i in range( len(Metric_types) ):
        ax3[i].set_xlabel('Local Buffer Size')
        ifact = cind/2.0-0.5
        ax3[i].set_xticks(ind+width*ifact); ax3[i].set_xticklabels(ticklabels)
        #ax3[i].set_yscale('log')

    if num_metrics>1:
        if orient == 0:
            ax3[0].legend(loc=9, bbox_to_anchor=(0.5, -1.38), ncol=2, shadow=True)
            plt.subplots_adjust(left=0.16, bottom=0.13, right=0.92, top=0.91, wspace=None, hspace=0.24)
        else:
            ax3[0].legend(loc=9, bbox_to_anchor=(1.1, -0.15), ncol=2, shadow=True)
            plt.subplots_adjust(left=0.08, bottom=0.24, right=0.96, top=None, wspace=None, hspace=None)
    else:
        ax3[0].legend(loc='best', shadow=True)

    # Name the figure appropriately
    namestr = 'figure'
    for metric in Metric_types:
        namestr = namestr+'_'+metric
    for opstr in allowed_ops:
        namestr = namestr+'_'+opstr
    filename = namestr+'_'+str(numdims)+'d_count'+str(count)+'_size'+str(size)+'mb_nodes'+str(nodes)+'_ppn'+str(ppn)
    f3.savefig(filename, dpi=100)

plt.show()
