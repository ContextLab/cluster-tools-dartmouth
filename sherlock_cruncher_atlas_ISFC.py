#!/usr/bin/python

import os
import sys
import numpy as np
import scipy.io as sio
from config2 import config
from isfc import timepoint_decoder
import glob

def load_helper(x):
    return np.array(np.load(x))

iternum = int(sys.argv[1])
condition = sys.argv[2]
save_file = os.path.join(config['resultsdir'], 'atlas_ISFC_results_' + condition + '_' + str(iternum) + '.npz')

if not os.path.isfile(save_file):
    # xval_groups = np.load(os.path.join(config['resultsdir'], 'xval_folds.npz'))['xval_groups']
    # params = np.load(os.path.join(config['resultsdir'], 'best_parameters.npz'))
    fnames = glob.glob(os.path.join(os.path.join(config['datadir'], 'atlas_files'), condition + '*.npy'))

    data = np.array(map(load_helper, fnames))
    results = timepoint_decoder(data[:, :, np.sum(np.isnan(np.sum(data, axis=0)), axis=0) == 0], windowsize=60, mu=1, nfolds=2)
    np.savez(save_file, results=results)
