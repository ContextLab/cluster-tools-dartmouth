#!/usr/bin/python

import os
import numpy as np
from itertools import zip_longest
from shutil import copy2
from eventseg_config import config

import matplotlib.pyplot as plt
import seaborn as sns
sns.set_context('talk')

kvals_dir = os.path.join(config['datadir'], 'k-values')
events_dir = os.path.join(config['datadir'], 'events')
eventseg_dir = os.path.join(config['datadir'], 'eventseg-models')
eventtimes_dir = os.path.join(config['datadir'], 'event-times')
optimized_dir = os.path.join(config['datadir'], 'optimized')
plot_dir = os.path.join(config['datadir'], 'plots')

# plot params
suptitles = {'atlep1' : 'Atlanta episode 1 immediate recall',
          'atlep2' : 'Atlanta episode 2 recall',
          'arrdev' : 'Arrested Development recall',
          'delayed' : 'Atlanta episode 1 delayed recall',
          'prediction' : 'Prediction'}

for d in [optimized_dir, plot_dir]:
    if not os.path.isdir(d):
        os.mkdir(d)

for root, dirs, files in os.walk(kvals_dir):
    # looking at each rectype
    if any(f.startswith('debug') for f in files):
        rectype = os.path.split(root)[-1]
        files = [file for file in files if file.startswith('debug')]
        print(f'optimizing {rectype}...')

        fig1, axarr1 = plt.subplots(nrows=len(files)//8+1, ncols=8, sharex=True, sharey=True)
        fig1.set_size_inches(len(axarr1[0])*4, len(axarr1)*4)
        fig1.suptitle(f'{suptitles[rectype]} correlations by k', y=1.02)
        axarr1 = axarr1.flatten()

        fig2, axarr2 = plt.subplots(nrows=len(files)//8+1, ncols=8)
        fig2.set_size_inches(len(axarr2[0])*4, len(axarr2)*4)
        fig1.suptitle(f'{suptitles[rectype]} k-optimization functions', y=1.02)
        axarr2 = axarr2.flatten()

        for i, (f, ax1, ax2) in enumerate(zip_longest(files, axarr1, axarr2)):
            if not f:
                ax1.axis('off')
                ax2.axis('off')
                continue

            kval_path = os.path.join(root, f)
            ks = np.load(kval_path)

            t = list(map(lambda x: x[0]/(x[1]+100), ks))
            t /= np.max(t)
            for j, v in enumerate(t):
                t[j] -= (j+2)/50
            max_k = np.argmax(t) + 2

            # select and organize corresponding files for optimal k
            turkid = f.split('-')[0]
            opt_events_path = os.path.join(events_dir, rectype, turkid, f'{max_k}.npy')
            opt_evseg_path = os.path.join(eventseg_dir, rectype, turkid, f'{max_k}.p')
            opt_times_path = os.path.join(eventtimes_dir, rectype, turkid, f'{max_k}.npy')

            for old_path in [opt_events_path, opt_evseg_path, opt_times_path]:
                split_old = old_path.split('/')
                new_path = os.path.join(optimized_dir, *split_old[-4:-2], f'{turkid}{os.path.splitext(old_path)[1]}')

                if not os.path.isdir(os.path.dirname(new_path)):
                    os.makedirs(os.path.dirname(new_path))

                copy2(old_path, new_path)

            # plotting
            ax1.plot([np.nan]*2 + list(map(lambda x: x[0], ks)), label='Within-event')
            ax1.plot([np.nan]*2 + list(map(lambda x: x[1], ks)), label='Across-events')
            ax1.legend()
            ax1.set_xlim(0, 51)
            ax1.set_ylim(0, 1)
            ax1.set_xticks(np.arange(0, 51, 10))
            ax1.set_title(f'P{i+1}')

            ax2.plot([np.nan]*2 + list(t))
            ax2.set_xlim(0, 51)
            ax2.set_ylim(0, 1)
            ax2.set_xticks(np.arange(0, 51, 10))
            ax2.set_title(f'P{i+1}: optimal k = {max_k}')

            # left column
            if not i % 8:
                ax1.set_ylabel('Correlation')
                ax1.set_yticks(np.arange(0, 1.1, .2))
                ax2.set_ylabel('Normalized\nwithin/across ratio')
                ax2.set_yticks(np.arange(0, 1.1, .2))
            else:
                ax1.set_ylabel('')
                ax2.set_ylabel('')
            # bottom row
            if i > len(files) - 9:
                ax1.set_xlabel('Number of events (k)')
                ax2.set_xlabel('Number of events (k)')
            else:
                ax1.set_xlabel('')
                ax1.set_xticklabels([])
                ax2.set_xlabel('')
                ax2.set_xticklabels([])

        fig1.tight_layout()
        fig1.subplots_adjust()
        fig1.savefig(os.path.join(plot_dir, f'{rectype}-corr-curves.pdf'), bbox_inches='tight')
        fig2.tight_layout()
        fig2.subplots_adjust()
        fig2.savefig(os.path.join(plot_dir, f'{rectype}-k-opt-curves.pdf'), bbox_inches='tight')
