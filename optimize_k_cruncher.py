#!/usr/bin/python

import os
import sys
import pickle
import traceback
import shutil
import numpy as np
from ast import literal_eval
from optimize_k_config import config

traj_name = sys.argv[1]

trajs_dir = os.path.join(config['datadir'], 'trajectories')
events_dir = os.path.join(config['datadir'], 'events')
eventseg_dir = os.path.join(config['datadir'], 'eventseg_models')
corrmat_dir = os.path.join(config['datadir'], 'corrmats')
boundaries_dir = os.path.join(config['datadir'], 'event_boundaries')
optimized_dir = os.path.join(config['datadir'], 'optimized')

traj_fp = os.path.join(trajs_dir, traj_name)
traj = np.load(traj_fp)

script = script = traj_name[:-9]
corrmat = np.load(os.path.join(corrmat_dir, f'{script}_corrmat.npy'))

scores = []
ks_list = []

script_eventsegs = os.listdir(os.path.join(eventseg_dir, script))
for eventseg in script_eventsegs:

    with open(os.path.join(eventseg_dir, script, eventseg), 'rb') as f:
        ev = pickle.load(f)

    k = int(eventseg.strip('.p').split('k')[-1])
    w = np.round(ev.segments_[0]).astype(int)
    mask = np.sum(list(map(lambda x: np.outer(x, x), w.T)), 0).astype(bool)
    within = corrmat[mask].mean()
    across = corrmat[~mask].mean()
    scores.append((within, across))
    ks_list.append(k)

t = list(map(lambda x: x[0]/(x[1]-(scores[0][0]/scores[0][1])), scores))
t /= np.max(t)
ratios = list(map(lambda x, y: x - y/250, t, ks_list))
maxk = ks_list[np.argmax(ratios)]

events_fp = os.path.join(events_dir, script, f'{script}_events_k{maxk}.npy')
shutil.copyfile(events_fp, os.path.join(optimized_dir, f'{script}_events.npy'))

boundaries_fp = os.path.join(boundaries_dir, script, f'{script}_boundaries_k{maxk}.txt')

with open(boundaries_fp, 'r') as f:
    boundaries = f.read().split('\n')[:-1]
boundaries = np.array([literal_eval(b) for b in boundaries])
np.save(os.path.join(optimized_dir, f'{script}_boundaries.npy'), boundaries)
