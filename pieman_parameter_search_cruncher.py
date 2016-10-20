#!/usr/bin/python

import os
import sys

import numpy as np
import scipy.io as sio
import isfc
from config import config

try:
    os.stat(config['resultsdir'])
except:
    os.makedirs(config['resultsdir'])

windowlength = int(sys.argv[1])
mu = float(sys.argv[2])
xval_file = sys.argv[3]

xval_groups = np.load(xval_file)['xval_groups']

data = sio.loadmat(os.path.join(config['datadir'], 'pieman_data.mat'), variable_names=('intact'))['intact'][0]

results_file = os.path.join(config['resultsdir'], "xvalresults_" + str(windowlength) + '_' + str(mu))
results = isfc.timepoint_decoder(data[xval_groups == 0], windowsize=windowlength, mu=mu, nfolds=2, connectivity_fun=isfc.isfc)

np.savez(results_file, results=results)
