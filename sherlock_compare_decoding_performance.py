import numpy as np
import pandas as pd
from config import config
import os
import scipy.io as sio
from glob import glob as lsdir
from scipy.stats import ttest_ind as ttest
from copy import copy

def parse_fname(fname, condition, features):
    fname = os.path.split(fname)[1]
    return int(fname[len(features[0] + '_results_' + condition + '_'):-4])

data = sio.loadmat(os.path.join(config['datadir'], 'sherlock_data.mat'))
ignore_keys = ('__header__', '__globals__', '__version__')
conditions = set(data.keys()) - set(ignore_keys)

features = ('voxel', 'baseline', 'isfc', 'mix')
iterations = []
for c in conditions:
    next_files = lsdir(os.path.join(config['resultsdir'], features[0] + '_results_' + c + '*.npz'))
    iterations = np.union1d(iterations, map(parse_fname, next_files, [c]*len(next_files), [features]*len(next_files)))

results = list()
for f in features:
    results_file = os.path.join(config['resultsdir'], 'collated_results_' + f + '.pkl')
    next_results = pd.read_pickle(results_file)
    accuracies = pd.DataFrame(index=iterations, columns=conditions)
    for c in conditions:
        accuracies[c] = next_results[c]['accuracy']
    results.append(accuracies)

columns = pd.MultiIndex.from_product([conditions, features], names=['conditions', 'features'])
t = pd.DataFrame(index=features, columns=columns)
p = pd.DataFrame(index=features, columns=columns)
for i in np.arange(len(features)):
    for j in np.arange(len(features)):
        if i == j:
            continue
        for k in conditions:
            a = results[i][k]
            b = results[j][k]

            next = ttest(a, b)
            t[k, features[i]][features[j]] = next[0]
            p[k, features[i]][features[j]] = next[1]
