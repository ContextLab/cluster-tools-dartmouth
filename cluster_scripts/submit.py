#!/usr/bin/python

# create a bunch of job scripts
import os
from datetime import datetime as dt
from os.path import dirname, realpath, join as opj
from string import Template
from subprocess import run
from .config import job_config as config

job_script = opj(dirname(realpath(__file__)), 'cruncher.py')
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
echo script name: $job_name
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
        self.scriptdir = self.config['scriptdir']
        self.lockdir = self.config['lockdir']
        self.hostname = os.environ.get('HOSTNAME')
        self.username = os.environ.get('LOGNAME')
        self.locks = []

        # set submission command
        if self.username.startswith('f00'):
            self.submit_cmd = 'mksub'
        else:
            self.submit_cmd = 'qsub'

        # create directories if they don't already exist
        try:
            os.stat(self.scriptdir)
        except FileNotFoundError:
            os.mkdir(self.scriptdir)
        try:
            os.stat(self.lockdir)
        except FileNotFoundError:
            os.mkdir(self.lockdir)

    def lock(self, job_name):
        lockfile_path = opj(self.lockdir, f'{job_name}.LOCK')
        self.locks.append(lockfile_path)
        try:
            os.stat(lockfile_path)
            return True
        except FileNotFoundError:
            with open(lockfile_path, 'w') as f:
                f.writelines(f'LOCK CREATE TIME: {dt.now()} \n')
                f.writelines(f'HOST: {self.hostname} \n')
                f.writelines(f'USER: {self.username} \n')
                f.writelines('\n-----\nCONFIG\n-----\n')
                for opt, val in self.config.items():
                    f.writelines(f'{opt.upper()} : {val} \n')
            return False

    def release_locks(self):
        for l in self.locks:
            os.remove(l)
        os.rmdir(self.lockdir)

    def submit_job(self, jobscript_path):
        submission_cmd = f'echo "[SUBMITTING JOB: {jobscript_path} ]"; {self.submit_cmd}'
        run([submission_cmd, jobscript_path])


    def write_scriptfile(self, job_name, job_command):
        filepath = opj(self.scriptdir, job_name)
        try:
            os.stat(filepath)
            return
        except FileNotFoundError:
            template_vals = self.config
            template_vals['job_name'] = job_name
            template_vals['job_command'] = job_command
            script_content = self.template.substitute(template_vals)
            with open(filepath, 'w+') as f:
                f.write(script_content)
            return filepath


script_template = ScriptTemplate(JOBSCRIPT_TEMPLATE, config)

for job_n, job_c in zip(job_names, job_commands):
    lockfile_exists = script_template.lock(job_n)
    if not lockfile_exists:
        script_filepath = script_template.write_scriptfile(job_n, job_c)
        if script_filepath:
            script_template.submit_job(script_filepath)

script_template.release_locks()
