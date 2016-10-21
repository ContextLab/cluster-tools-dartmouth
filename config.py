import socket
import os

config = dict()
config['template'] = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'run_job.sh')

# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
# job creation options

if (socket.gethostname() == 'discovery') or (socket.gethostname() == 'ndoli'):
    config['datadir'] = '/idata/cdl/data/fMRI/pieman/'
    config['workingdir'] = '/idata/cdl/jmanning/pieman_analysis/'
    config['startdir'] = '/idata/cdl/jmanning'
else:
    config['datadir'] = '/Users/jmanning/Desktop/fMRI/pieman'
    config['workingdir'] = config['datadir']
    config['startdir'] = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))  # directory to start the job in

config['scriptdir'] = os.path.join(config['workingdir'], 'scripts')
config['lockdir'] = os.path.join(config['workingdir'], 'locks')
config['resultsdir'] = os.path.join(config['workingdir'], 'results')


# runtime options
config['jobname'] = "piemanISFC"  # default job name
config['q'] = "default"  # options: default, testing, largeq
config['nnodes'] = 1  # how many nodes to use for this one job
config['ppn'] = 1  # how many processors to use for this one job (assume 4GB of RAM per processor)
config['walltime'] = '0:30:00'  # maximum runtime, in h:MM:SS
config['cmd_wrapper'] = "python"  # replace with actual command wrapper (e.g. matlab, python, etc.)

#extra options

# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
