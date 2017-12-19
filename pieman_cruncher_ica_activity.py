#!/usr/bin/python

import os
import sys
import numpy as np
import scipy.io as sio
from config import config
from isfc import timepoint_decoder

iternum = int(sys.argv[1])
condition = sys.argv[2]
k = 50
save_file = os.path.join(config['resultsdir'], 'ica' + str(k) + '_activity_results_' + condition + '_' + str(iternum) + '.npz')

if not os.path.isfile(save_file):
    # xval_groups = np.load(os.path.join(config['resultsdir'], 'xval_folds.npz'))['xval_groups']
    # params = np.load(os.path.join(config['resultsdir'], 'best_parameters.npz'))
    data = sio.loadmat(os.path.join(config['datadir'], 'pieman_ica' + str(k) + '.mat'))[condition][0]

    # if condition == "intact":
    #    data = data[np.where(xval_groups != 0)]

    # windowsize from Simony et al., 2016
    results = timepoint_decoder(data, windowsize=60, mu=0, nfolds=2)
    np.savez(save_file, results=results)
