#!/usr/bin/python

import os
import sys
import pickle
import numpy as np
import brainiak.eventseg.event as event
from eventseg_config import config

def reduce_model(m, ev):
    w = (np.round(ev.segments_[0])==1).astype(bool)
    return np.array([m[wi, :].mean(0) for wi in w.T])

traj_path, min_k, max_k = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

rectype = traj_path.split('/')[-2]
traj_name = os.path.splitext(traj_path.split('/')[-1])[0]
kvals_path = os.path.join(config['datadir'], 'k-values', rectype, f'{traj_name}-kvals.npy')
events_dir = os.path.join(config['datadir'], 'events', rectype, traj_name)
eventseg_dir = os.path.join(config['datadir'], 'eventseg-models', rectype, traj_name)
eventtimes_dir = os.path.join(config['datadir'], 'event-times', rectype, traj_name)

traj = np.load(traj_path)
corrmat = np.corrcoef(traj)

ks = list(range(min_k, max_k+1))
scores = np.zeros((len(ks), 3))

for i, k in enumerate(ks):
    ev = event.EventSegment(k)
    ev.fit(traj)
    events = reduce_model(traj, ev)
    i1, i2 = np.where(np.round(ev.segments_[0])==1)
    w = np.zeros_like(ev.segments_[0])
    w[i1,i2] = 1
    w = np.dot(w, w.T).astype(bool)
    within = corrmat[w].mean()
    across = corrmat[~w].mean()
    scores[i] = (within, across, within/across)

    event_times = []
    for s in ev.segments_[0].T:
        try:
            tp = np.where(np.round(s)==1)[0]
        # deal with error caused by overfitting predictions high k-values
        except IndexError:
            tp = [np.nan, np.nan]
        event_times.append((tp[0], tp[-1]))

    np.save(os.path.join(events_dir, f'{k}.npy'), events)
    np.save(os.path.join(eventtimes_dir, f'{k}.npy'), np.array(event_times))
    with open(os.path.join(eventseg_dir, f'{k}.p'), 'wb') as f:
        pickle.dump(ev, f)

np.save(kvals_path, scores)
