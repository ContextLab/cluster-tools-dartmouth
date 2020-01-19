#!/usr/bin/python

# create a bunch of job scripts
import getpass
import os
import socket
import datetime as dt
from os.path import dirname, realpath, join as opj
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

script_dir = config['scriptdir']
lock_dir = config['lockdir']
template_script = config['template']

# use largeq if more than 600 jobs are being submitted (Discovery policy)
if len(job_commands) > 600 and config['queue'] == 'default':
    config['queue'] = 'largeq'

# set command to activate conda env
if config['env_type'] == 'conda':
    config['env_cmd'] = 'source activate'
else:
    raise ValueError("Only conda environments are currently supported")

# create script directory if it doesn't already exist
try:
    os.stat(script_dir)
except FileNotFoundError:
    os.makedirs(script_dir)

lock_dir_exists = False


def _create_helper(s):
    opens_ix = [i for i, char in enumerate(s) if char == '<']
    closes_ix = [i for i, char in enumerate(s) if char == '>']
    # return line if it contains no replaceable options
    if len(opens_ix) == 0:
        return s

    q = ''
    index = 0
    for i in range(len(opens_ix)):
        q += s[index:opens_ix[i]]
        unpacked = eval(s[opens_ix[i] + 1:y[i]])
        q += str(unpacked)
        index = closes_ix[i] + 1
    return q


def create_job(name):

    template_fd = open(template_script, 'r')
    job_fname = opj(script_dir, name)
    new_fd = open(job_fname, 'w+')

    while True:
        next_line = template_fd.readline()
        if len(next_line) == 0:
            break
        new_fd.writelines(_create_helper(next_line))
    template_fd.close()
    new_fd.close()
    return job_fname


def lock(lockfile):
    try:
        os.stat(lockfile)
        return False
    except FileNotFoundError:
        fd = open(lockfile, 'w')
        fd.writelines('LOCK CREATE TIME: ' + str(dt.datetime.now()) + '\n')
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


try:
    os.stat(lock_dir)
    lock_dir_exists = True
except FileNotFoundError:
    os.makedirs(lock_dir)

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

# all jobs have been submitted; release all locks
for l in locks:
    release(l)
if not lock_dir_exists:  # remove lock directory if it was created here
    os.rmdir(lock_dir)
