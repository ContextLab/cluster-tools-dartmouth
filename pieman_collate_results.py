#!/usr/bin/python

import numpy as np
import os
import fnmatch

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
save_file = os.path.join(results_dir, 'results.npz')

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


    unique_mus = np.unique(mus)
    unique_ws = np.unique(windowlengths)

    errors = np.zeros((unique_mus.size, unique_ws.size))
    ranks = np.zeros((unique_mus.size, unique_ws.size))
    accuracies = np.zeros((unique_mus.size, unique_ws.size))

    for i in range(len(results)):
        mu_ind = np.where(unique_mus == mus[i])
        w_ind = np.where(unique_ws == windowlengths[i])

        r = np.load(os.path.join(results_dir, results[i]))['results'].tolist()
        errors[mu_ind, w_ind] = r['error']
        ranks[mu_ind, w_ind] = r['rank']
        accuracies[mu_ind, w_ind] = r['accuracy']

    np.savez(save_file, mu=unique_mus, w=unique_ws, errors=errors, ranks=ranks, accuracies=accuracies)
