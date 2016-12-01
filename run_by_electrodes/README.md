## scripts to submit multiple jobs for each subject - by electrode number
## same as previous script, with a worker.py script to loop through the number of electrodes for each subject.

## to submit:
bash cruncher_electrode.sh

1. this runs each each electrode for each subject as an individual job
	- calls on worker.py that finds number of electrode for a subject
1. calls on casenumber and electrode_number which is defined in the bash script
1. casenumber iterates over each .npz file with complete path
1. electrode_number iterates over each electrode for that subject
1. each casenumber and electrode number is added to a job script
1. job script submits:
    python print.py $casenumber $electrode_number radius k_threshold

## print.py needs to be substituted.  This is only a test.
