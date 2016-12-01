#!/usr/bin/env python

import numpy as np
import sys



def main(fname):
	data = np.load(fname, mmap_mode='r')
	n_electrodes = np.shape(data['R'])[0]-1
	print n_electrodes
	sys.exit(n_electrodes)

if __name__ == "__main__":
	main(sys.argv[1])