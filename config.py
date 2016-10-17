config = dict()

config['template'] = 'run_job.sh'

# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
# job creation options
config['scriptdir'] = '/idata/cdl/jmanning/brain-dynamics-model/jobs/'
config['lockdir'] = '/idata/cdl/jmanning/brain-dynamics-model/jobs/locks/'

# runtime options
config['jobname'] = "piemanISFC_param_search"  # default job name
config['q'] = "default"  # options: default, testing, largeq
config['nnodes'] = 1  # how many nodes to use for this one job
config['ppn'] = 1  # how many processors to use for this one job (assume 4GB of RAM per processor)
config['walltime'] = '0:10:00'  # maximum runtime, in h:MM:SS
config['startdir'] = '/idata/cdl/jmanning/brain-dynamics-model'  # directory to start the job in
config['cmd_wrapper'] = "python"  # replace with actual command wrapper (e.g. matlab, python, etc.)
config['modules'] = "(\"python/2.7.11\")"  # separate each module with a space and enclose in (escaped) double quotes
# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
