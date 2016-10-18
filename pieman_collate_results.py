#!/usr/bin/python

import numpy as np
import pandas as pd
import os
import fnmatch
import matplotlib.pyplot as plt
import seaborn as sb

def parse_fname(fname):
    x = [i for i, char in enumerate(fname) if char == '_']
    assert(len(x) == 1)
    x = x[0]

    try:
        w = int(fname[0:x])
        mu = float(fname[x+1:-4])
    except:
        mu = []
        w = []
    return np.array(mu), np.array(w)


results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'results')
fig_dir = os.path.join(results_dir, 'figs')
save_file = os.path.join(results_dir, 'results.pkl')

if not os.path.isfile(save_file):
    results = list()
    mus = np.array([])
    windowlengths = np.array([])

    for file in os.listdir(results_dir):
        if fnmatch.fnmatch(file, '*.npz'):
            mu, w = parse_fname(file)
            if mu.size == 0:
                continue

            results.append(file)
            mus = np.append(mus, mu)
            windowlengths = np.append(windowlengths, w)

    results = pd.DataFrame({'errors': np.array(map((lambda x: np.load(os.path.join(results_dir, x))['results'].tolist()['error']), results)),
                       'accuracies': np.array(map((lambda x: np.load(os.path.join(results_dir, x))['results'].tolist()['accuracy']), results)),
                       'ranks': np.array(map((lambda x: np.load(os.path.join(results_dir, x))['results'].tolist()['rank']), results)),
                       'mu': mus,
                       'windowlength': windowlengths})
    results.to_pickle(save_file)

results = pd.read_pickle(save_file)

# compile results
xval_ranks = results.pivot('windowlength', 'mu', 'ranks')
xval_errors = results.pivot('windowlength', 'mu', 'errors')
xval_accuracies = results.pivot('windowlength', 'mu', 'accuracies')

# make fig_dir if it doesn't already exist
try:
    os.stat(fig_dir)
except:
    os.makedirs(fig_dir)

# print out cross validation figures
plt.close()
xval_ranks_fig = sb.heatmap(xval_ranks)
xval_ranks_fig.get_figure().savefig(os.path.join(fig_dir, 'xval_ranks_fig.pdf'))

plt.close()
xval_errors_fig = sb.heatmap(xval_errors)
xval_errors_fig.get_figure().savefig(os.path.join(fig_dir, 'xval_errors_fig.pdf'))

plt.close()
xval_accuracies_fig = sb.heatmap(xval_accuracies)
xval_accuracies_fig.get_figure().savefig(os.path.join(fig_dir, 'xval_accuracies_fig.pdf'))


# best parameters are the ones that yield the highest classification accuracy
accuracies = xval_accuracies.values
best_inds = np.where(accuracies == np.max(accuracies))
best_windowlength = int(xval_accuracies.index[best_inds[0]].tolist()[0])
best_mu = round(xval_accuracies.columns[best_inds[1]].tolist()[0], 10)

np.savez(os.path.join(results_dir, 'best_parameters'), windowlength=best_windowlength, mu=best_mu)


