#!/usr/bin/python

#a simple python job:
# + sleeps for 2 seconds
# + creates a file in the current working directory called <JOBNUM>.results, where <JOBNUM> is the input argument
from time import sleep
import sys
import os

results_file = sys.argv[1]+'.results'

if not os.path.isfile(results_file):
    sleep(2)

    fd = open(results_file, 'w+')
    fd.write(sys.argv[1]+'\n')
    fd.close()

