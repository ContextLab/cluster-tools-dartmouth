#!/usr/bin/python

import os
import subprocess
import traceback
import pandas as pd
from helpers import cleanup_text, wipe_formatting

data = pd.read_csv(os.path.join(config['datadir'], 'data.csv')

errors = dict()
for title in data.title:
    t = title.replace(' ','-')
    job = f'scripts/transform_{t}.sh'
    if (os.path.isfile(job) and not os.path.isfile(f'../data/trajectories/{t}_traj.npy')
        and len(cleanup_text(wipe_formatting(data.loc[data.title==title, 'script'].values[0]))) > 8528):
        try:
            job_cmd = 'echo "[SUBMITTING JOB: ' + job + ']"; mksub'
            subprocess.call(job_cmd + " " + job, shell=True)
        except Exception as e:
            print(e)
            errors[title] = traceback.format_exc(e)

if errors:
    with open('output_errors.txt', 'w') as f:
        for script, error in errors:
            f.write(f'{script}:\n\t{error}\n{"-"*20}\n')
