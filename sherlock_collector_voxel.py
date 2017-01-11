import numpy as np
import pandas as pd
from config import config
import os
from glob import glob as lsdir
import seaborn as sb
import scipy.io as sio
from matplotlib import rcParams as pltconfig

pltconfig['pdf.fonttype'] = 42

def parse_fname(fname, condition):
    fname = os.path.split(fname)[1]
    return int(fname[len('voxel_results_' + condition + '_'):-4])

fig_dir = os.path.join(config['resultsdir'], 'figs')

data = sio.loadmat(os.path.join(config['datadir'], 'sherlock_data.mat'))
ignore_keys = ('__header__', '__globals__', '__version__')
conditions = set(data.keys()) - set(ignore_keys)

columns = pd.MultiIndex.from_product([conditions, ['error', 'accuracy', 'rank']], names=['conditions', 'metric'])
results_file = os.path.join(config['resultsdir'], 'collated_results_voxel.pkl')

iterations = []
for c in conditions:
    next_files = lsdir(os.path.join(config['resultsdir'], 'voxel_results_' + c + '*.npz'))
    iterations = np.union1d(iterations, map(parse_fname, next_files, [c]*len(next_files)))

if not os.path.isfile(results_file):
    results = pd.DataFrame(index=iterations, columns=columns)
    for c in conditions:
        for t in iterations:
            next_file = os.path.join(config['resultsdir'], 'voxel_results_' + c + '_' + str(int(t)) + '.npz')
            if os.path.isfile(next_file):
                try:
                    next_results = np.load(next_file)['results'].item()
                    results.set_value(t, (c, 'error'), next_results['error'])
                    results.set_value(t, (c, 'accuracy'), next_results['accuracy'])
                    results.set_value(t, (c, 'rank'), next_results['rank'])
                except:
                    continue
    results.to_pickle(results_file)

results = pd.read_pickle(results_file)

accuracies = pd.DataFrame(index=iterations, columns=conditions)
for c in conditions:
    accuracies[c] = results[c]['accuracy']

sb.set(font_scale=1.5)
ax = sb.barplot(data=accuracies, color='k')
ax.set(xlabel='Condition', ylabel='Decoding accuracy')
sb.plt.ylim(0, 0.16)
sb.plt.savefig(os.path.join(fig_dir, 'decoding_accuracy_voxel.pdf'))
