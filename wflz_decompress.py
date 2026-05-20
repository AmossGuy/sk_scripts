#!/usr/bin/env python3

import io
import struct
import sys

def wflz_decompress(data):
	writer = io.BytesIO()
	
	magic = data[0:4]
	if magic == b"ZLFW":
		raise ValueError("chunked wflz format is not supported by this script")
	elif magic != b"WFLZ":
		raise ValueError("unknown magic. are you sure this is wflz data?")
	
	(compressed_size, decompressed_size) = struct.unpack("<II", data[4:4+8])
	
	# TODO
	
	decompressed_data = writer.getvalue()
	writer.close()
	return decompressed_data

if __name__ == "__main__":
	if len(sys.argv) != 2:
		print("tool requires exactly one argument: the path to some wflz data to decompress")
		print("the decompressed version is created adjacent to that file")
		sys.exit(1)
	
	path = sys.argv[1]
	with open(path, "rb") as f:
		data = f.read()
	
	compressed = wflz_decompress(data)
	with open(f"{path} decompressed", "wb") as f:
		f.write(compressed)
	
	print("success!")
