import numpy as np
import pandas as pd
import scipy.io as sio
from config import config
from python.isfc import timepoint_decoder
import os

xval_groups = np.load(os.path.join(config['resultsdir'], 'xval_folds.npz'))['xval_groups']
fig_dir = os.path.join(config['resultsdir'], 'figs')
params = np.load(os.path.join(config['resultsdir'], 'best_parameters.npz'))

data = sio.loadmat(os.path.join(config['datadir'], 'pieman_data.mat'))
ignore_keys = ('__header__', '__globals__', '__version__')
conditions = set(data.keys()) - set(ignore_keys)

save_file = os.path.join(config['resultsdir'], 'opt_results_' + condition + '_' + str(iternum))



n_iterations = 10
iterations = np.arange(n_iterations)

ignore_keys = ('__header__', '__globals__', '__version__')
conditions = set(data.keys()) - set(ignore_keys)

columns = pd.MultiIndex.from_product([conditions, ['error', 'accuracy', 'rank']], names=['conditions', 'metric'])

results_file = os.path.join(results_dir, 'collated_results.pkl')

if not os.path.isfile(results_file):
    results = pd.DataFrame(index=iterations, columns=columns)
    for c in conditions:
        next_data = data[c][0]
        if c == "intact":
            next_data = next_data[np.where(xval_groups != 0)]

        for t in iterations:
            next_results = timepoint_decoder(next_data, windowsize=params['windowlength'].tolist(),
                                             mu=params['mu'].tolist(), nfolds=2)
            results[c]['error'][t] = next_results['error']
            results[c]['accuracy'][t] = next_results['accuracy']
            results[c]['rank'][t] = next_results['rank']
    results.to_pickle(results_file)

results = pd.read_pickle(results_file)