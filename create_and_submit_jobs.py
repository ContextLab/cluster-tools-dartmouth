#!/usr/bin/python

# create a bunch of job scripts
import datetime as dt
import getpass
import os
import socket
from subprocess import call

import numpy as np
import scipy.io as sio
from config import config
from python.isfc import get_xval_assignments

basedir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
w = sio.loadmat(os.path.join(basedir, 'weights700.mat'))['weights'][0]
n_folds = 3
xval_groups = get_xval_assignments(len(w), nfolds=n_folds)

results_dir = os.path.join(basedir, 'results')
# noinspection PyBroadException
try:
    os.stat(results_dir)
except:
    os.makedirs(results_dir)

xval_file = os.path.join(results_dir, 'xval_folds.npz')
np.savez(xval_file, xval_groups=xval_groups)

# each job command should be formatted as a string
job_script = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pieman_parameter_search.py')

windowlengths = np.arange(10, 110, 10)
mus = np.arange(0, 1.1, 0.1)

job_commands = list()
job_names = list()
for w in windowlengths:
    for m in mus:
        job_commands.append(job_script + " " + str(w) + " " + str(m) + " " + xval_file)
        job_names.append('pieman_' + str(w) + '_' + str(m) + '.sh')
# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======

assert(len(job_commands) == len(job_names))


# job_command is referenced in the run_job.sh script
# noinspection PyBroadException,PyUnusedLocal
def create_job(name, job_command):
    # noinspection PyUnusedLocal,PyShadowingNames
    def create_helper(s, job_command):
        x = [i for i, char in enumerate(s) if char == '<']
        y = [i for i, char in enumerate(s) if char == '>']
        if len(x) == 0:
            return s

        q = ''
        index = 0
        for i in range(len(x)):
            q += s[index:x[i]]
            unpacked = eval(s[x[i]+1:y[i]])
            q += str(unpacked)
            index = y[i]+1
        return q

    # create script directory if it doesn't already exist
    try:
        os.stat(config['scriptdir'])
    except:
        os.makedirs(config['scriptdir'])

    template_fd = open(config['template'], 'r')
    job_fname = os.path.join(config['scriptdir'], name)
    new_fd = open(job_fname, 'w+')

    while True:
        next_line = template_fd.readline()
        if len(next_line) == 0:
            break
        new_fd.writelines(create_helper(next_line, job_command))
    template_fd.close()
    new_fd.close()
    return job_fname


# noinspection PyBroadException
def lock(lockfile):
    try:
        os.stat(lockfile)
        return False
    except:
        fd = open(lockfile, 'w')
        fd.writelines('LOCK CREATE TIME: ' + str(dt.datetime.now()) + '\n')
        fd.writelines('HOST: ' + socket.gethostname() + '\n')
        fd.writelines('USER: ' + getpass.getuser() + '\n')
        fd.writelines('\n-----\nCONFIG\n-----\n')
        for k in config.keys():
            fd.writelines(k.upper() + ': ' + str(config[k]) + '\n')
        fd.close()
        return True


# noinspection PyBroadException
def release(lockfile):
    try:
        os.stat(lockfile)
        os.remove(lockfile)
        return True
    except:
        return False


script_dir = config['scriptdir']
lock_dir = config['lockdir']
lock_dir_exists = False
# noinspection PyBroadException
try:
    os.stat(lock_dir)
    lock_dir_exists = True
except:
    os.makedirs(lock_dir)

# noinspection PyBroadException
try:
    os.stat(config['startdir'])
except:
    os.makedirs(config['startdir'])

locks = list()
for n, c in zip(job_names, job_commands):
    # if the submission script crashes before all jobs are submitted, the lockfile system ensures that only
    # not-yet-submitted jobs will be submitted the next time this script runs
    next_lockfile = os.path.join(lock_dir, n+'.LOCK')
    locks.append(next_lockfile)
    if not os.path.isfile(os.path.join(script_dir, n)):
        if lock(next_lockfile):
            next_job = create_job(n, c)

            if (socket.gethostname() == 'discovery') or (socket.gethostname() == 'ndoli'):
                submit_command = 'echo "[SUBMITTING JOB: ' + next_job + ']"; qsub'
            else:
                submit_command = 'echo "[RUNNING JOB: ' + next_job + ']"; sh'

            call(submit_command + " " + next_job, shell=True)

# all jobs have been submitted; release all locks
for l in locks:
    release(l)
if not lock_dir_exists:  # remove lock directory if it was created here
    os.rmdir(lock_dir)
