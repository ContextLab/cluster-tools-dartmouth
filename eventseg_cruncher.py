#!/usr/bin/python

import os
import sys
import pickle
import numpy as np
import brainiak.eventseg.event as event

script_name, k = sys.argv[1], int(sys.argv[2])

traj_path = os.path.join(config['datadir'], 'trajectories', f'{script_name}_traj.npy')
traj = np.load(traj_path)

ev = event.EventSegment(k)
ev.fit(traj)
w = (np.round(ev.segments_[0])==1).astype(bool)
segs = np.array([traj[wi, :].mean(0) for wi in w.T])

segments_filepath = os.path.join(config['datadir'], 'segments', script_name, f'{script_name}_events_k{str(k)}.npy'
eventseg_filepath = os.path.join(config['datadir'], 'eventseg_models', script_name, f'{script_name}_eventseg_k{str(k)}.p'

np.save(segments_filepath, segs)
with open(eventseg_filepath, 'wb') as f:
    pickle.dump(ev)






# import sys
# import joblib
# import numpy as np
# import pandas as pd
# from scipy.signal import resample
# from eventseg_config import config
# from helpers import *
#
# id = sys.argv[1]
# wsize = 50
#
# # load only single row to save time & memory
# skiprows = range(1, id)
# data = pd.read_csv(os.path.join(config['datadir'], 'data.csv'), skiprows=skiprows, nrows=1).T.squeeze()
# name = data.title
#
# # remove HTML formatting, clean script content
# clean_script = cleanup_text(wipe_formatting(data.script))
#
# # don't model empty scripts (8,528 characters is length of shortest cleaned script)
# if len(clean_script) < 8528:
#     sys.exit()
#
# cv = joblib.load(os.path.join(config['datadir'], 'fit_cv.joblib'))
# lda = joblib.load(os.path.join(config['datadir'], 'fit_lda_t100.joblib'))
#
# sentences = cleaned.split('.')
# windows = []
# for ix, _ in enumerate(sentences):
#     windows.append(' '.join(sentences[ix:ix+wsize]))
#
#
# script_tf = cv.transform(windows)
# script_traj = resample(lda.transform(script_tf), 1000)
# corrmat = np.corrcoef(script_traj)
#
# np.save(os.path.join(config['datadir'], 'trajectories', f'{name}_traj.npy'), script_traj)
# np.save(os.path.join(config['datadir'], 'corrmats', f'{name}_corrmat.npy'), corrmat)
