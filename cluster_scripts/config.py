from os.path import dirname, realpath, join as opj

job_config = dict()

# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
# job creation options
job_config['startdir'] = # path to the remote foler for this project.  Should be something like /dartfs/rc/lab/D/DBIC/CDL/<your_net_id>/<project_name>
job_config['datadir'] = opj(job_config['startir'], 'data')
job_config['workingdir'] = opj(job_config['startir'], 'scripts')
job_config['template'] = opj(dirname(realpath(__file__)), 'run_job_cluster.sh')
job_config['scriptdir'] = opj(job_config['workingdir'], 'scripts')
job_config['lockdir'] = opj(job_config['workingdir'], 'locks')

# runtime options
job_config['jobname'] = # (str) default job name
job_config['q'] =   # (str) options: default, test, largeq (when in doubt, use "largeq")
job_config['nnodes'] = # (int) how many nodes to use for this one job
job_config['ppn'] = # (int) how many processors to use for this one job (assume 4GB of RAM per processor)
job_config['walltime'] =  # (str) maximum runtime, in h:MM:SS (e.g., "10:00:00")
job_config['cmd_wrapper'] =  # (str) replace with actual command wrapper (e.g. "python", "matlab", etc.)
job_config['modules'] = # (str) modules you need to load for your scripts separated by a space (e.g., "python matlab")
job_config['env_type'] = # (str) what kind of Python environment you use (NOTE: sole option is currently "conda" -- "venv" and "virtualenv" coming soon!)
job_config['env_name'] = # (str) names of (currently, conda) environment you want your submission script and jobs to run in
# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
