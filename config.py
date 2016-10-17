import socket
import os

config = dict()
config['template'] = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'run_job.sh')

# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
# job creation options
config['startdir'] = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) # directory to start the job in

if (socket.gethostname() == 'discovery') or (socket.gethostname() == 'ndoli'):
    config['scriptdir'] = '/idata/cdl/jmanning/brain-dynamics-model/jobs/'
    config['lockdir'] = '/idata/cdl/jmanning/brain-dynamics-model/jobs/locks/'
else:
    config['scriptdir'] = '/Users/jmanning/Desktop/fMRI/pieman/scripts'
    config['lockdir'] = '/Users/jmanning/Desktop/fMRI/pieman/locks/'

# runtime options
config['jobname'] = "piemanISFC_param_search"  # default job name
config['q'] = "default"  # options: default, testing, largeq
config['nnodes'] = 1  # how many nodes to use for this one job
config['ppn'] = 1  # how many processors to use for this one job (assume 4GB of RAM per processor)
config['walltime'] = '0:10:00'  # maximum runtime, in h:MM:SS
config['cmd_wrapper'] = "python"  # replace with actual command wrapper (e.g. matlab, python, etc.)
config['modules'] = "(\"python/2.7.11\")"  # separate each module with a space and enclose in (escaped) double quotes
# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
