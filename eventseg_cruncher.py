#!/usr/bin/python

import sys
import os
import pickle
import numpy as np
import brainiak.eventseg.event as event
from eventseg_config import config

filepath, k = sys.argv[1], sys.argv[2]
dir, f_name  = os.path.split(filepath)
rectype = os.path.split(dir)[1]
trajectory = np.load(filepath)
savepath = os.path.join(config['resultsdir'], rectype, os.path.splitext(f_name)[0], 'k'+k+'.npy')

if not os.path.isfile(savepath):
    ev = event.EventSegment(int(k))
    ev.fit(trajectory)

    np.save(savepath, ev.segments_[0])
