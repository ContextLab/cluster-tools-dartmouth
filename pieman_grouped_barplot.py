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
    return int(fname[len('baseline_results_' + condition + '_'):-4])

fig_dir = os.path.join(config['resultsdir'], 'figs')

data = sio.loadmat(os.path.join(config['datadir'], 'pieman_data.mat'))
ignore_keys = ('__header__', '__globals__', '__version__')
conditions = set(data.keys()) - set(ignore_keys)

iterations = []
for c in conditions:
    next_files = lsdir(os.path.join(config['resultsdir'], 'baseline_results_' + c + '*.npz'))
    iterations = np.union1d(iterations, map(parse_fname, next_files, [c] * len(next_files)))

metrics = ('voxel', 'baseline', 'isfc', 'mix')
columns = pd.MultiIndex.from_product([conditions, metrics], names=['Condition', 'Feature type'])

combined_results_file = os.path.join(config['resultsdir'], 'combined_results.pkl')

if not os.path.isfile(combined_results_file):
    results = pd.DataFrame(index=iterations, columns=columns)
    for m in metrics:
        results_file = os.path.join(config['resultsdir'], 'collated_results_' + m + '.pkl')
        next_results = pd.read_pickle(results_file)

        accuracies = pd.DataFrame(index=iterations, columns=conditions)
        for c in conditions:
            results[c, m] = next_results[c]['accuracy']

    results.to_pickle(combined_results_file)

results = pd.read_pickle(combined_results_file)

sb.set(font_scale=1.5)
h = sb.barplot(data=pd.melt(results), x="Condition", y="value", hue="Feature type", palette=sb.cubehelix_palette(len(conditions)))
h.set_ylabel('Decoding accuracy')
sb.plt.savefig(os.path.join(fig_dir, 'decoding_accuracy.pdf'))