#!/usr/bin/python

# create a bunch of job scripts
from eventseg_config import config
from subprocess import call
import os
import socket
import getpass
import datetime as dt


# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======
k_range = list(range(2,75))

# split each script into 3 jobs, segmentation runtime increases with k
# first does first 50% of k's, second does middle 30%, third does final 20%
start = k_range[0]
div1 = len(k_range)//2
div2 = int(len(k_range)*.8)
stop = k_range[-1]

job_commands = list()
job_names = list()
job_script = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'eventseg_cruncher.py')

segments_dir = os.path.join(config['datadir'], 'segments')
eventseg_models_dir = os.path.join(config['datadir'], 'eventseg_models')

if not os.path.isdir(segments_dir):
    os.mkdir(segments_dir)

if not os.path.isdir(eventseg_models_dir):
    os.mkdir(eventseg_models_dir)

traj_dir = os.path.join(config['datadir'], 'trajectories')
script_names = [f.rstrip('_traj.npy') for f in os.listdir(traj_dir) if f.endswith('traj.npy')]

for s in script_names:
    scriptseg_dir = os.path.join(segments_dir, s)
    script_eventsegs_dir = os.path.join(eventseg_models_dir, s)
    if not os.path.isdir(scriptseg_dir)
        os.mkdir(scriptseg_dir)
    if not os.path.isdir(script_eventsegs_dir)
        os.mkdir(script_eventsegs_dir)

    job_commands.append(f'{job_script} {s} {start} {div1}')
    job_names.append(f'segment_{s}_1')

    job_commands.append(f'{job_script} {s} {div1} {div2}')
    job_names.append(f'segment_{s}_2')

    job_commands.append(f'{job_script} {s} {div2} {stop}')
    job_names.append(f'segment_{s}_3')

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
