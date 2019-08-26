#!/usr/bin/python

import os
import pickle
import traceback
import numpy as np
import pandas as pd
from ast import literal_eval
from eventseg_config import config

trajs_dir = os.path.join(config['datadir'], 'trajectories')
events_dir = os.path.join(config['datadir'], 'events')
eventseg_dir = os.path.join(config['datadir'], 'eventseg_models')
corrmat_dir = os.path.join(config['datadir'], 'corrmats')
boundaries_dir = os.path.join(config['datadir'], 'event_boundaries')

ks_list = list(range(2, 76))

data_df = pd.DataFrame(columns=['title', 'trajectory', 'n_events', 'events', 'event_boundaries'],
    index=list(range(len(os.listdir(eventseg_dir)))))

for i, script in enumerate(os.listdir(eventseg_dir)):
    data_df.loc[i, 'title'] = script.replace('-', ' ')

    traj_fp = os.path.join(trajs_dir, f'{script}_traj.npy')
    data_df.loc[i, 'trajectory'] = np.load(traj_fp)

    scores = []
    for k in ks_list:
        eventseg_fp = os.path.join(eventseg_dir, script, f'{script}_eventseg_k{k}.p')
        try:
            with open(eventseg_fp, 'rb') as f:
                ev = pickle.load(f)

            corrmat = np.load(os.path.join(corrmat_dir, f'{script}_corrmat.npy'))
            w = np.round(ev.segments_[0]).astype(int)
            mask = np.sum(list(map(lambda x: np.outer(x, x), w.T)), 0).astype(bool)
            within = corrmat[mask].mean()
            ra = corrmat[~mask].mean()
            scores.append((within, across))

        except Exception as e:
            traceback.print_exc()
            scores.append(np.nan)

    t = list(map(lambda x: x[0]/(x[1]-(scores[0][0]/scores[0][1])), scores))
    t /= np.max(t)
    ratios = list(map(lambda x: x - k/250, t))

    maxk = ks_list[np.argmax(ratios)]
    data_df.loc[i, 'n_events'] = maxk

    events_fp = os.path.join(events_dir, script, f'{script}_events_k{maxk}.npy')
    data_df.loc[i, 'events'] = np.load(events_fp)

    boundaries_fp = os.path.join(boundaries_dir, script, f'{script}_boundaries_k{maxk}.txt')
    with open(boundaries_fp, 'r') as f:
        boundaires = f.read().split('\n')[:-1]
    boundaries = [literal_eval(b) for b in boundaries]
    data_df.loc[i, 'event_boundaries'] = boundaries

data_df.to_csv('finished_data.csv')
