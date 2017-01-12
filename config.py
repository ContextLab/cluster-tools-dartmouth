import socket
import os

config = dict()

# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
# job creation options

if (socket.gethostname() == 'vertex') or (socket.gethostname() == 'vertex.kiewit.dartmouth.edu') or (socket.gethostname() == 'vertex.local'):
    config['datadir'] = '/Users/jmanning/Desktop/fMRI/pieman/'
    config['workingdir'] = config['datadir']
    config['startdir'] = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))  # directory to start the job in
    config['template'] = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'run_job_local.sh')
else:
    config['datadir'] = '/idata/cdl/data/fMRI/sherlock/'
    config['workingdir'] = '/idata/cdl/jmanning/sherlock_analysis/'
    config['startdir'] = '/idata/cdl/jmanning'
    config['template'] = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'run_job_cluster.sh')

config['scriptdir'] = os.path.join(config['workingdir'], 'scripts')
config['lockdir'] = os.path.join(config['workingdir'], 'locks')
config['resultsdir'] = os.path.join(config['workingdir'], 'results')


# runtime options
config['jobname'] = "sherlock_decoding"  # default job name
config['q'] = "largeq"  # options: default, test, largeq
config['nnodes'] = 1  # how many nodes to use for this one job
config['ppn'] = 16  # how many processors to use for this one job (assume 4GB of RAM per processor)
config['walltime'] = '10:00:00'  # maximum runtime, in h:MM:SS
config['cmd_wrapper'] = "python"  # replace with actual command wrapper (e.g. matlab, python, etc.)

#extra options

# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
