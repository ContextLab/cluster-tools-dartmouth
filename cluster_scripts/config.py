from os.path import dirname, realpath, join as opj

job_config = dict()

# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
# directory location
job_config['startdir'] =        # (str) path to the remote foler for this project.
                                # Should be something like /dartfs/rc/lab/D/DBIC/CDL/<your_net_id>/<project_name>

# job environment options
job_config['modules'] =         # (str) modules you need to load for your scripts
                                # separated by a space (e.g., "python matlab")
job_config['env_type'] =        # (str) what kind of Python environment you use
                                # (NOTE: sole option is currently "conda" -- "venv"
                                # and "virtualenv" coming soon!)
job_config['env_name'] =        # (str) names of (currently, conda) environment
                                # you want your submission script and jobs to run in
job_config['cmd_wrapper'] =     # (str) replace with actual command wrapper
                                # (e.g. "python", "matlab", etc.)

# runtime options
job_config['jobname'] =         # (str) default job name
job_config['queue'] =           # (str) options: default, test, largeq
                                # (when in doubt, use "largeq")
job_config['nnodes'] =          # (int) how many nodes to use for this one job
job_config['ppn'] =             # (int) how many processors to use for this one
                                # job (assume 4GB of RAM per processor)
job_config['walltime'] =        # (str) maximum runtime, in h:MM:SS
                                # (e.g., "10:00:00")

# Email update options
job_config['email_updates'] =   # (str) what events you want to receive email
                                # notifications about (see below)
job_config['email_addr'] =      # (str or None) email address where you want job
                                # notifications sent (see below)

# Torque (the cluster's resource manager) can send you emails about the status
# of your job.  These emails will come from "root" (torque@northstar.dartmouth.edu).
# To set your notification preferences for the current batch of to-be-submitted
# jobs, set the 'email_updates' value to a *single* string that consists of some
# combination of the following options:
#   + "a" - notify me when a job is aborted (Torque default behavior)
#   + "b" - notify me when a job begins
#   + "e" - notify me when a job finishes

# If you would like to receive emails for any of these events, set the value of
# 'email_addr' to the address you'd like to receive them
# To receive no emails from Torque, set 'email_updates' to "n" (no mail) and
# 'email_addr' to None

# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======

job_config['datadir'] = opj(job_config['startir'], 'data')
job_config['workingdir'] = opj(job_config['startir'], 'scripts')
job_config['template'] = opj(dirname(realpath(__file__)), 'run_job_cluster.sh')
job_config['scriptdir'] = opj(job_config['workingdir'], 'scripts')
job_config['lockdir'] = opj(job_config['workingdir'], 'locks')