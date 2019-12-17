#!/usr/bin/python

from eventseg_config import config
import os
import numpy as np
import pandas as pd

segments_df = pd.DataFrame()

for root, dirs, files in os.walk(eventseg_config['resultsdir']):
    event_models = [f for f in files if f.endswith('.npy')]
    if event_models:
        ep_path, turkid = os.path.split(root)
        ep_name = os.path.split(ep_path)[1]
        multiindex = pd.MultiIndex.from_product([[ep_name], [turkid]])
        tmp_df = pd.DataFrame(index=multiindex, columns=[os.path.splitext(em)[0] for em in event_models])
        for e in event_models:
            ev_mod = np.load(os.path.join(root,e))
            tmp_df.at[(ep_name,turkid), os.path.splitext(e)[0]] = ev_mod

        segments_df = segments_df.append(tmp_df)

segments_df.to_pickle(os.path.join(config['resultsdir'],'segments_df.p')
