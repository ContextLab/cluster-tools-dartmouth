#!/bin/bash

python /idata/cdl/jmanning/brain-dynamics-model/cluster/pieman_submit_atlas_activity.py
python /idata/cdl/jmanning/brain-dynamics-model/cluster/pieman_submit_atlas_mix.py
python /idata/cdl/jmanning/brain-dynamics-model/cluster/pieman_submit_atlas_ISFC.py

python /idata/cdl/jmanning/brain-dynamics-model/cluster/pieman_submit_ica_activity.py
python /idata/cdl/jmanning/brain-dynamics-model/cluster/pieman_submit_ica_mix.py
python /idata/cdl/jmanning/brain-dynamics-model/cluster/pieman_submit_ica_ISFC.py

python /idata/cdl/jmanning/brain-dynamics-model/cluster/sherlock_submit_atlas_activity.py
python /idata/cdl/jmanning/brain-dynamics-model/cluster/sherlock_submit_atlas_mix.py
python /idata/cdl/jmanning/brain-dynamics-model/cluster/sherlock_submit_atlas_ISFC.py

python /idata/cdl/jmanning/brain-dynamics-model/cluster/sherlock_submit_ica_activity.py
python /idata/cdl/jmanning/brain-dynamics-model/cluster/sherlock_submit_ica_mix.py
python /idata/cdl/jmanning/brain-dynamics-model/cluster/sherlock_submit_ica_ISFC.py
