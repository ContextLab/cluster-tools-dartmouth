import numpy as np
import pandas as pd
from config import config
import os
import scipy.io as sio

data = sio.loadmat(os.path.join(config['datadir'], 'pieman_data.mat'))
ignore_keys = ('__header__', '__globals__', '__version__')
conditions = set(data.keys()) - set(ignore_keys)

features = ('voxel', 'baseline', 'isfc', 'mix')

results = list()
for f in features:
    results_file = os.path.join(config['resultsdir'], 'collated_results_' + f + '.pkl')
    next_results = pd.read_pickle(results_file)
    accuracies = pd.DataFrame(index=iterations, columns=conditions)
    for c in conditions:
        accuracies[c] = results[c]['accuracy']
    results.append(accuracies)



