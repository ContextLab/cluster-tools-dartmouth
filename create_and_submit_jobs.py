#create a bunch of job scripts
import config
import os
import socket
from subprocess import call

######## CUSTOMIZE THE CODE BETWEEN THESE LINES ########
#each job command should be formatted as a string
job_commands = map(lambda x: x[0]+" "+str(x[1]), zip(["test.py"]*10, range(10)))

#job_names should specify the file name of each script (as a list, of the same length as job_commands)
job_names = map(lambda x: str(x)+'.sh', range(len(job_commands)))
######## CUSTOMIZE THE CODE BETWEEN THESE LINES ########

assert(len(job_commands) == len(job_names))


def create_job(name, job_command, config):
    def create_helper(s, config):
        x = [i for i, char in enumerate(s) if char == '[']
        y = [i for i, char in enumerate(s) if char == ']']
        if len(x) == 0: return s

        q = ''
        index = 0
        for i in range(len(x)):
            q += s[index:x[i]-2]
            unpacked = eval(s[x[i]:y[i]-1])
            q += unpacked
            index = y[i]
        return q

    #create script directory if it doesn't already exist
    try:
        os.stat(config.scriptdir)
    except:
        os.mkdir(config.scriptdir)

    template_fd = open(config.template, 'r')
    job_fname = os.path.join(config.scriptdir, name)
    new_fd = open(job_fname, 'w+')

    while True:
        next = template_fd.readline()
        if next is None: break
        new_fd.writelines(create_helper(next, config))
    template_fd.close()
    new_fd.close()
    return job_fname


for n,c in zip(job_names, job_commands):
    next_job = create_job(n, c, config)

    if (socket.gethostname() == 'discovery') or (socket.gethostname() == 'ndoli'):
        submit_command = 'echo "[SUBMITTING JOB]"; qsub'
    else:
        submit_command = 'echo "[RUNNING JOB]"; sh'

    call(submit_command, next_job)


