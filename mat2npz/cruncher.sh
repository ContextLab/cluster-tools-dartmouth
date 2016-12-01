#!/bin/bash
# This script generates jobs
# input: name of directories

for i in /idata/cdl/data/ECoG/pyFR/data/mat/*.mat
do
  	qsub -v casenumber=$i -N my_case$i_job sub_jobs.pbs
done