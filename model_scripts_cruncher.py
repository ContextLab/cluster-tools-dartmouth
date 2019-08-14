#!/usr/bin/python

import sys
import joblib
import numpy as np
import pandas as pd
from scipy.signal import resample
from model_scripts_config import config
from helpers import *

id = int(sys.argv[1])
wsize = 50

# load only single row to save time & memory
skiprows = range(1, id)
data = pd.read_csv(os.path.join(config['datadir'], 'data.csv'), skiprows=skiprows, nrows=1).T.squeeze()
name = data.title

# remove HTML formatting, clean script content
clean_script = cleanup_text(wipe_formatting(data.script))

# don't model empty scripts (8,528 characters is length of shortest cleaned script)
if len(clean_script) < 8528:
    sys.exit()

cv = joblib.load(os.path.join(config['datadir'], 'fit_cv.joblib'))
lda = joblib.load(os.path.join(config['datadir'], 'fit_lda_t100.joblib'))

sentences = clean_script.split('.')
windows = []
for ix, _ in enumerate(sentences):
    windows.append(' '.join(sentences[ix:ix+wsize]))


script_tf = cv.transform(windows)
script_traj = resample(lda.transform(script_tf), 1000)
corrmat = np.corrcoef(script_traj)

np.save(os.path.join(config['datadir'], 'trajectories', f'{name.replace(" ","-")}_traj.npy'), script_traj)
np.save(os.path.join(config['datadir'], 'corrmats', f'{name.replace(" ","-")}_corrmat.npy'), corrmat)
