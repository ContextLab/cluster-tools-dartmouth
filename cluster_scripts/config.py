import socket
import os

config = dict()

# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
# job creation options

#add additional checks for your local machine here...
# ******** check kiewit hostname from eduroam ********
if (socket.gethostname() == 'Paxtons-MacBook-Pro') or (socket.gethostname() == 'Paxtons-MacBook-Pro.kiewit.dartmouth.edu') or (socket.gethostname() == 'Paxtons-MacBook-Pro.local'):
    config['datadir'] = '/Users/paxtonfitzpatrick/Documents/Dartmouth/Thesis/memory-dynamics/data/models/participants/trajectories'
    config['workingdir'] = config['datadir']
    config['startdir'] = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))  # directory to start the job in
    config['template'] = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'run_job_local.sh')
else:
    config['datadir'] = os.path.join('/dartfs/rc/lab/D/DBIC/CDL/f0028ph/eventseg', 'trajectories')
    config['workingdir'] = '/dartfs/rc/lab/D/DBIC/CDL/f0028ph/eventseg/cluster-scripts'
    config['startdir'] = '/dartfs/rc/lab/D/DBIC/CDL/f0028ph/eventseg/'
    config['template'] = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'run_job_cluster.sh')

config['scriptdir'] = os.path.join(config['workingdir'], 'scripts')
config['lockdir'] = os.path.join(config['workingdir'], 'locks')
config['resultsdir'] = os.path.join(config['workingdir'], 'results')


# runtime options
config['jobname'] = "eventseg"  # default job name
config['q'] = "largeq"  # options: default, test, largeq
config['nnodes'] = 1  # how many nodes to use for this one job
config['ppn'] = 4  # how many processors to use for this one job (assume 4GB of RAM per processor)
config['walltime'] = '20:00:00'  # maximum runtime, in h:MM:SS
config['cmd_wrapper'] = "python"  # replace with actual command wrapper (e.g. matlab, python, etc.)

#extra options

# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
