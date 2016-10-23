#!/bin/bash -l

# DO NOT MODIFY THIS FILE!

# Portable Batch System (PBS) lines begin with "#PBS".  to-be-replaced text is sandwiched between angled brackets

# declare a name for this job
#PBS -N <config['jobname']>

# specify the queue the job will be added to (if more than 600, use largeq)
#PBS -q <config['q']>

# specify the number of cores and nodes (estimate 4GB of RAM per core)
#PBS -l nodes=<config['nnodes']>:ppn=<config['ppn']>

# specify how long the job should run (wall time)
#PBS -l walltime=<config['walltime']>

# set the working directory *of the job* to the specified start directory
cd <config['startdir']>

declare cluster1='discovery'
declare cluster2='ndoli'
if [ "$HOSTNAME" == "$cluster1" ] || [ "$HOSTNAME" == "$cluster2" ]; then
    echo ----
    echo LOADING PYTHON 2.7.11
    module load python/2.7.11

    echo ACTIVATING BRAIN DYNAMICS MODEL VIRTUAL ENVIRONMENT
    source activate hobd

    echo UNLOADING PYTHON 2.7.11
    module unload python/2.7.11

    echo PYTHON PATH CONFIGURATION COMPLETE
    echo ----
fi

# run the job
<config['cmd_wrapper']> <job_command> #note: job_command is reserved for the job command; it should not be specified in config.py

if [ "$HOSTNAME" == "$cluster1" ] || [ "$HOSTNAME" == "$cluster2" ]; then
    source deactivate hobd
fi
