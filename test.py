#!/usr/bin/python

#a simple python job:
# + sleeps for 5 seconds
# + creates a file in the current working directory called <JOBNUM>.results, where <JOBNUM> is the input argument
from time import sleep
import sys

sleep(5)

fd = open(sys.argv[1]+'.results', 'w+')
fd.write(sys.argv[1]+'\n')
fd.close()
