from file_io import mat2npz
import sys

def main(infile, outfile):
	mat2npz(infile, outfile)


if __name__ == "__main__":
	main(sys.argv[1], sys.argv[2])