#!/usr/bin/python

import os
import sys
import numpy as np
import scipy.io as sio
from config2 import config
from isfc import timepoint_decoder

condition = sys.argv[1]
iternum = int(sys.argv[2])
mu = float(sys.argv[3])
save_file = os.path.join(config['resultsdir'], 'opt_results_' + condition + '_' + str(iternum) + '_' +str(mu) + '.npz')

if not os.path.isfile(save_file):
    data = sio.loadmat(os.path.join(config['datadir'], 'sherlock_data.mat'))[condition][0]

    results = timepoint_decoder(data, windowsize=60, mu=mu, nfolds=2)
    np.savez(save_file, results=results)

