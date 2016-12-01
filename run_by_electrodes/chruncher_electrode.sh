#!/bin/bash
# This script generates jobs
# input: name of directories
# it also uses the worker_electrode.py script to loop over all the electrodes in the

for i in /idata/cdl/data/ECoG/pyFR/data/npz/BW001.npz
do
    electrode=$(python worker_electrode.py $i>&1)
        for e in $(seq 1 $electrode)
        do
  	        qsub -v casenumber=$i,electrode_number=$e -N my_case$i_job jobs_electrodes.pbs
        done
done