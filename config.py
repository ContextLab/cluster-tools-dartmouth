config = dict()

######## CUSTOMIZE THE OPTIONS BETWEEN THESE LINES ########
#job creation options
config['scriptdir'] = '/scratch/myname/myjob/'
config['lockdir'] = '/scratch/myname/myjob/locks/'
config['template'] = 'run_job.sh'


#runtime options
config['jobname'] = "myjob" #default job name
config['q'] = "default" #options: default, testing, largeq
config['nnodes'] = 1 #how many nodes to use for this one job
config['ppn'] = 1 #how many processors to use for this one job (assume 4GB of RAM per processor)
config['walltime'] = '0:00:30' #maximum runtime, in h:MM:SS
config['startdir'] = '/scratch/myname/myjob' #directory to start the job in
config['cmd_wrapper'] = "python" #replace with actual command wrapper (e.g. matlab, python, etc.)
config['modules'] = "(""python/2.7.11"")" #separate each module with a space and *two* double quotes
######## CUSTOMIZE THE OPTIONS BETWEEN THESE LINES ########