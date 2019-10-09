#!/usr/bin/python

# create a bunch of job scripts
from embedding_config import config
from subprocess import call
import os
import socket
import getpass
import datetime as dt
from os.path import join as opj


# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
job_script = opj(os.path.dirname(os.path.realpath(__file__)), 'embedding_cruncher.py')

embeddings_dir = opj(config['datadir'], 'embeddings')
fig_dir = opj(config['datadir'], 'figures')

job_commands = list()
job_names = list()
# range of possible k-values to search over (inclusive)
np_seeds = list(range(2000))

rectypes = ['atlep1', 'atlep2', 'arrdev', 'delayed']

for d in [embeddings_dir, fig_dir]:
    if not os.path.isdir(d):
        os.mkdir(d)
        for rectype in rectypes:
            if not os.path.isdir(opj(d, rectype)):
                os.mkdir(opj(d, rectype))

for ns in np_seeds:
    exists = False
    for rectype in rectypes:
        if all(os.path.isfile(opj(embeddings_dir, rectype, f'np{ns}_umap{0}.p')) for rectype in rectypes):
            exists = True
    if not exists:
        job_commands.append(f'{job_script} {ns}')
        job_names.append(f'optimize_embedding_numpy{ns}')


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
    job_fname = opj(config['scriptdir'], name)
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
    next_lockfile = opj(lock_dir, n+'.LOCK')
    locks.append(next_lockfile)
    if not os.path.isfile(opj(script_dir, n)):
        if lock(next_lockfile):
            next_job = create_job(n, c)

            if ('discovery' in socket.gethostname()) or ('ndoli' in socket.gethostname()):
                submit_command = 'echo "[SUBMITTING JOB: ' + next_job + ']"; mksub'
            else:
                submit_command = 'echo "[RUNNING JOB: ' + next_job + ']"; sh'

            call(submit_command + " " + next_job, shell=True)

# all jobs have been submitted; release all locks
for l in locks:
    release(l)
if not lock_dir_exists:  # remove lock directory if it was created here
    os.rmdir(lock_dir)