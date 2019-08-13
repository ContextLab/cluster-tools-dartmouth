#!/usr/bin/python

# create a bunch of job scripts
from eventseg_config import config
from subprocess import call
import os
import socket
import getpass
import datetime as dt


# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======

job_commands = list()
job_names = list()
job_script = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'eventseg_cruncher.py')

segments_dir = os.path.join(config['datadir'], 'segments')
eventseg_models_dir = os.path.join(config['datadir'], 'eventseg_models')

try:
    os.mkdir(segments_dir)
except FileExistsError:
    pass

try:
    os.mkdir(eventseg_models_dir)
except FileExistsError:
    pass

traj_dir = os.path.join(config['datadir'], 'trajectories')
script_names = [f.rstrip('_traj.npy') for f in os.listdir(traj_dir) if f.endswith('traj.npy')]

for s in script_names:
    scriptseg_dir = os.path.join(segments_dir, s)
    script_eventsegs_dir = os.path.join(eventseg_models_dir, s)
    try:
        os.mkdir(scriptseg_dir)
    except FileExistsError:
        pass
    try:
        os.mkdir(script_eventsegs_dir)
    except FileExistsError:
        pass

    for k in range(2, 75):
        job_commands.append(f'{job_script} {s} {str(k)}')
        job_names.append(f'segment_{s}_k{str(k)}')

# import pandas as pd
# from helpers import download_from_google_drive as dl
#
# # download pre-trained CountVectorizer and LatentDirichletAllocation models
# cv_id = '1qD27Os44vojkC0UUf2cYlDZ5XytotGbK'
# cv_dest = os.path.join(config['datadir'], 'fit_cv.joblib')
# lda_id = '1iu7X84Hd1y6Vhz8xtG2nZZ_OSolkjz9g'
# lda_dest = os.path.join(config['datadir'], 'fit_lda_t100.joblib')
# dl(cv_id, cv_dest)
# dl(lda_id, lda_dest)
#
# job_script = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'eventseg_cruncher.py')
#
# for output in ['trajectories', 'corrmats']:
#     if not os.path.isdir(os.path.join(config['datadir'], output)):
#         os.mkdir(os.path.join(config['datadir'], output))
#
# # load in and clean data
# data_df = pd.read_csv(os.path.join(config['datadir'], 'data.csv'))
# data_df.dropna(subset=['script'], inplace=True)
# data_df.drop_duplicates(subset=['title'], inplace=True)
#
# job_commands = list()
# job_names = list()
#
# for _, row in data_df.iterrows():
#     job_commands.append(f'{job_script} {row.id}')
#     job_names.append(f'transform_{row.title}.sh')


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
                submit_command = 'echo "[SUBMITTING JOB: ' + next_job + ']"; mksub'
            else:
                submit_command = 'echo "[RUNNING JOB: ' + next_job + ']"; sh'

            call(submit_command + " " + next_job, shell=True)

# all jobs have been submitted; release all locks
for l in locks:
    release(l)
if not lock_dir_exists:  # remove lock directory if it was created here
    os.rmdir(lock_dir)
