import numpy as np
import pandas as pd
from config2 import config
import os
from glob import glob as lsdir
import seaborn as sb
import scipy.io as sio
from matplotlib import rcParams as pltconfig

pltconfig['pdf.fonttype'] = 42

def parse_iter(fname, condition):
    fname = os.path.split(fname)[1]
    params = (fname[len('opt_results_' + condition + '_'):-4])
    split_ind = params.find('_')
    return int(params[0:split_ind])


def parse_mu(fname, condition):
    fname = os.path.split(fname)[1]
    params = (fname[len('opt_results_' + condition + '_'):-4])
    split_ind = params.find('_')
    return float(params[split_ind+1:])

fig_dir = os.path.join(config['resultsdir'], 'figs')

data = sio.loadmat(os.path.join(config['datadir'], 'sherlock_data.mat'))
ignore_keys = ('__header__', '__globals__', '__version__')
conditions = set(data.keys()) - set(ignore_keys)

iterations = []
mus = []
for c in conditions:
    next_files = lsdir(os.path.join(config['resultsdir'], 'opt_results_' + c + '*.npz'))
    iterations = np.union1d(iterations, map(parse_iter, next_files, [c] * len(next_files)))
    mus = np.union1d(mus, map(parse_mu, next_files, [c] * len(next_files)))

columns = pd.MultiIndex.from_product([conditions, mus], names=['conditions', 'mu'])
results_file = os.path.join(config['resultsdir'], 'mu_search_results.pkl')

if not os.path.isfile(results_file):
    results = pd.DataFrame(index=iterations, columns=columns)
    for c in conditions:
        for t in iterations:
            for m in mus:
                next_file = os.path.join(config['resultsdir'], 'opt_results_' + c + '_' + str(int(t)) + '_' + str(m) + '.npz')
                if os.path.isfile(next_file):
                    try:
                        next_results = np.load(next_file)['results'].item()
                        results.set_value(t, (c, m), next_results['accuracy'])
                    except:
                        continue
    results.to_pickle(results_file)

results = pd.read_pickle(results_file)
sb.set(font_scale=1.25)
fig = sb.barplot(x="mu", y="value", hue="conditions", data=pd.melt(results))
fig.set_aspect(50)
fig.set(xlabel='$\mu$', ylabel='Decoding accuracy')
sb.plt.ylim(0, 0.2)
sb.plt.savefig(os.path.join(fig_dir, 'sherlock_decoding_accuracy_by_mu.pdf'))
