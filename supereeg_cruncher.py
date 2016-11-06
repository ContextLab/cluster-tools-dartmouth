#!/usr/bin/python

import os
from config import config

try:
    os.stat(config['resultsdir'])
except:
    os.makedirs(config['resultsdir'])

#TODO: write analysis here