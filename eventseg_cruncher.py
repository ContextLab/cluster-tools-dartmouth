#!/usr/bin/python

import os
import sys
import pickle
import numpy as np
import brainiak.eventseg.event as event
from eventseg_config import config

script_name, start_k, stop_k = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
traj_path = os.path.join(config['datadir'], 'trajectories', f'{script_name}_traj.npy')
traj = np.load(traj_path)
k_range = range(start_k, stop_k)

for k in k_range:
    ev = event.EventSegment(k)
    ev.fit(traj)
    w = (np.round(ev.segments_[0])==1).astype(bool)
    segs = np.array([traj[wi, :].mean(0) for wi in w.T])

    event_boundaries = []
    for s in ev.segments_[0].T:
        tp = np.where(np.round(s)==1)[0]
        event_boundaries.append((tp[0], tp[-1]))

    events_filepath = os.path.join(config['datadir'], 'events', script_name, f'{script_name}_events_k{str(k)}.npy')
    eventseg_filepath = os.path.join(config['datadir'], 'eventseg_models', script_name, f'{script_name}_eventseg_k{str(k)}.p')
    boundaries_filepath = os.path.join(config['datadir'], 'event_boundaries', script_name, f'{script_name}_boundaries_k{str(k)}.txt')

    np.save(events_filepath, segs)
    with open(eventseg_filepath, 'wb') as f:
        pickle.dump(ev, f)
    with open(boundaries_filepath, 'w') as f:
        for b in event_boundaries:
            f.write(f'{str(b)}\n')
