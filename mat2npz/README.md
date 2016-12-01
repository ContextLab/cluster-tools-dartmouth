# Convert .mat to .npz files

## to submit:
bash cruncher.sh

1. this runs each file conversion as an individual job
1. calls on casenumber, which is defined in the bash script
1 .casenumber iterates over each .mat file with complete path
1 .each casenumber is added to a job script
1 .job script is modified to:
    python file_converter.py $casenumber 'output path'

## file_converter.py contains a main file converter script
creates .npz files from .mat  with:
Y
R
fname_labels
samplerate

### THIS DID NOT INCLUDE THE OTHER FIELDS IN THE MAT FILES!
the reason for this had to do with the way the files, specifically the characters were stored in a format that makes it difficult to recover them

