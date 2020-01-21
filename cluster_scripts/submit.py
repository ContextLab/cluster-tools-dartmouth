#!/usr/bin/python

# create a bunch of job scripts
import os
import socket
from datetime import datetime as dt
from os.path import dirname, realpath, join as opj
from string import Template
from subprocess import run
from .config import job_config as config

job_script = opj(dirname(realpath(__file__)), 'embedding_cruncher.py')
job_name = config['jobname']

job_commands = list()
job_names = list()

# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======

# Write your job submission code here.
# Your submission code should:
#   + create the desired directory structure for your jobs' output files
#   + iterate over the combinations of parameters with which you want to run jobs
#   + for each parameter combination, append strings to the job_names and
#     job_commands lists
#     - items added to the job_names list should take the format:
#       '{job_name}_{param1}_{param2}'
#     - items added to the job_commands list should take the format:
#       '{job_script} {param1} {param2}'

# The code below will create a bash script for each combination of paramaters
# (named for the items in job_names) and place it in the scripts/ directory.
# Each bash script is submitted to the job queue to run on a compute node with
# the options specified in config.py.  These bash scripts, in turn, call your
# cruncher.py script with the arguments specified in job_commands.


# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
assert (len(job_commands) == len(job_names)), \
    "job_names and job_commands must have equal numbers of items"

# use largeq if more than 600 jobs are being submitted (Discovery policy)
if len(job_commands) > 600 and config['queue'] == 'default':
    config['queue'] = 'largeq'

# set command to activate conda env
if config['env_type'] == 'conda':
    config['activate_cmd'] = 'source activate'
    config['deactivate_cmd'] = 'conda deactivate'
else:
    raise ValueError("Only conda environments are currently supported")


JOBSCRIPT_TEMPLATE = Template(
"""#!/bin/bash -l
#PBS -N ${jobname}
#PBS -q ${queue}
#PBS -l nodes=${nnodes}:ppn=${ppn}
#PBS -l walltime=${walltime}
#PBS -m $email_updates
#PBS -M $email_addr

echo ---
job name: $job_name
echo loading modules: $modules
module load $modules

echo activating ${env_type} environment: $env_name
$activate_cmd $env_name

echo calling job script
$cmd_wrapper $job_command
echo job script finished
$deactivate_cmd
echo ---"""
)


class ScriptTemplate:
    def __init__(self, template, config):
        self.template = template
        self.config = config
        self.hostname = socket.gethostname()
        self.username = os.environ.get('LOGNAME')

    def write_scriptfile(self, job_name, job_command):
        template_vals = self.config
        template_vals['job_name'] = job_name
        template_vals['job_command'] = job_command

        script_content = self.template.substitute(template_vals)
        filepath = opj(template_vals['scriptdir'], job_name)
        with open(filepath, 'w+') as f:
            f.write(script_content)

        return filepath

    def lock(self, job_name):
        lockfile_path = opj(self.config['lockdir'], f'{job_name}.LOCK')
        try:
            os.stat(lockfile_path)
        except FileNotFoundError:
            



def lock(lockfile):
    try:
        os.stat(lockfile)
        return False
    except FileNotFoundError:
        fd = open(lockfile, 'w')
        fd.writelines('LOCK CREATE TIME: ' + str(dt.now()) + '\n')
        fd.writelines('HOST: ' + socket.gethostname() + '\n')
        fd.writelines('USER: ' + getpass.getuser() + '\n')
        fd.writelines('\n-----\nCONFIG\n-----\n')
        for k in config.keys():
            fd.writelines(k.upper() + ': ' + str(config[k]) + '\n')
        fd.close()
        return True


def release(lockfile):
    try:
        os.stat(lockfile)
        os.remove(lockfile)
        return True
    except FileNotFoundError:
        return False



script_dir = config['scriptdir']
lock_dir = config['lockdir']
template_script = config['template']
# create directories if they don't already exist
try:
    os.stat(script_dir)
except FileNotFoundError:
    os.makedirs(script_dir)

try:
    os.stat(lock_dir)
    lock_dir_exists = True
except FileNotFoundError:
    os.makedirs(lock_dir)


script_template = ScriptTemplate(JOBSCRIPT_TEMPLATE, config)


for n, c in zip(job_names, job_commands):
    script_template.lock




locks = list()
for n, c in zip(job_names, job_commands):
    # if the submission script crashes before all jobs are submitted, the lockfile system ensures that only
    # not-yet-submitted jobs will be submitted the next time this script runs
    next_lockfile = opj(lock_dir, n+'.LOCK')
    locks.append(next_lockfile)
    if not os.path.isfile(opj(script_dir, n)):
        if lock(next_lockfile):
            next_job = create_job(n, c)

            if ('discovery' in socket.gethostname()) or ('ndoli' in socket.gethostname()):
                submit_command = 'echo "[SUBMITTING JOB: ' + next_job + ']"; mksub'
            else:
                submit_command = 'echo "[RUNNING JOB: ' + next_job + ']"; sh'

            run(submit_command + " " + next_job, shell=True)

# all jobs have been submitted; release all locks...
for l in locks:
    release(l)
# ...and remove the lock directory
os.rmdir(lock_dir)
