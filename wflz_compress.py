#!/usr/bin/env python3

import sys
from sk_include.wflz import wflz_compress

if __name__ == "__main__":
	if len(sys.argv) != 2:
		print("tool requires exactly one argument: the path to some raw data to compress")
		print("the compressed version is created adjacent to that file")
		sys.exit(1)
	
	path = sys.argv[1]
	with open(path, "rb") as f:
		data = f.read()
	
	compressed = wflz_compress(data)
	with open(f"{path}.wflz", "wb") as f:
		f.write(compressed)
	
	print("success!")
