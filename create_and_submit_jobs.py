#!/usr/bin/python

#create a bunch of job scripts
from config import config
import os
import socket
from subprocess import call
import getpass

######## CUSTOMIZE THE CODE BETWEEN THESE LINES ########
#each job command should be formatted as a string
job_commands = map(lambda x: x[0]+" "+str(x[1]), zip(["test.py"]*10, range(10)))

#job_names should specify the file name of each script (as a list, of the same length as job_commands)
job_names = map(lambda x: str(x)+'.sh', range(len(job_commands)))
######## CUSTOMIZE THE CODE BETWEEN THESE LINES ########

assert(len(job_commands) == len(job_names))


def create_job(name, job_command, config):
    def create_helper(s, job_command, config):
        x = [i for i, char in enumerate(s) if char == '<']
        y = [i for i, char in enumerate(s) if char == '>']
        if len(x) == 0: return s

        q = ''
        index = 0
        for i in range(len(x)):
            q += s[index:x[i]]
            unpacked = eval(s[x[i]+1:y[i]])
            q += str(unpacked)
            index = y[i]
        return q

    #create script directory if it doesn't already exist
    try:
        os.stat(config['scriptdir'])
    except:
        os.makedirs(config['scriptdir'])

    template_fd = open(config['template'], 'r')
    job_fname = os.path.join(config['scriptdir'], name)
    new_fd = open(job_fname, 'w+')

    while True:
        next = template_fd.readline()
        if len(next) == 0: break
        new_fd.writelines(create_helper(next, job_command, config))
    template_fd.close()
    new_fd.close()
    return job_fname


def lock(lockfile):
    try:
        os.stat(lockfile)
        return False
    except:
        fd = open(lockfile, 'w')
        fd.writelines('LOCK CREATE TIME: ' + str(dt.datetime.now()))
        fd.writelines('HOST: ' + socket.gethostname())
        fd.writelines('USER: ' + getpass.getuser())
        fd.writelines('\n-----\nCONFIG\n-----')
        for k in config.keys():
            fd.writelines(k.upper() + ': ' + str(config[k]))
        return True


def release(lockfile):
    try:
        os.stat(lockfile)
        os.remove(lockfile)
        return True
    except:
        return False


script_dir = config['scriptdir']
lock_dir = config['lockdir']
try:
    os.stat(lock_dir)
except:
    os.makedirs(lock_dir)

locks = list()
for n,c in zip(job_names, job_commands):
    #if the submission script crashes before all jobs are submitted, the lockfile system ensures that only
    #not-yet-submitted jobs will be submitted the next time this script runs
    next_lockfile = os.path.join(lock_dir, n+'.LOCK')
    locks.append(next_lockfile)
    if not os.path.isfile(os.path.join(script_dir, n)):
        if lock(next_lockfile):
            next_job = create_job(n, c, config)

            if (socket.gethostname() == 'discovery') or (socket.gethostname() == 'ndoli'):
                submit_command = 'echo "[SUBMITTING JOB]"; qsub'
            else:
                submit_command = 'echo "[RUNNING JOB]"; sh'

            call(submit_command, next_job)

#all jobs have been submitted; release all locks
for l in locks:
    release(l)

