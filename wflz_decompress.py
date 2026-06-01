#!/usr/bin/env python3

import sys
from sk_include.wflz import wflz_decompress

if __name__ == "__main__":
	if len(sys.argv) != 2:
		print("tool requires exactly one argument: the path to some wflz data to decompress")
		print("the decompressed version is created adjacent to that file")
		sys.exit(1)
	
	path = sys.argv[1]
	with open(path, "rb") as f:
		decompressed = wflz_decompress(f)
	with open(f"{path} decompressed", "wb") as f:
		f.write(decompressed)
	
	print("success!")
