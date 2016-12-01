import numpy as np
import glob
import os
import sys


def main(fname, electrode, r, k_thresh):
	file_name = os.path.splitext(os.path.basename(fname))[0]
	print(file_name, electrode, str(r), str(k_thresh))
if __name__ == "__main__":
	main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])