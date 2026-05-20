#!/usr/bin/env python3

import io
import struct
import sys

def wflz_decompress(reader):
	output = bytearray(b"")
	
	magic = reader.read(4)
	if magic == b"ZLFW":
		raise ValueError("chunked wflz format is not supported by this script")
	elif magic != b"WFLZ":
		raise ValueError("unknown magic. are you sure this is wflz data?")
	
	(compressed_size, decompressed_size) = struct.unpack("<II", reader.read(8))
	
	while True:
		block = reader.read(4)
		if block == b"\0\0\0\0":
			break
		
		(backref_dist, backref_length, literal_count) = struct.unpack("<HBB", block)
		literals = reader.read(literal_count)
		
		output.extend(literals)
		# TODO: handle backrefs
	
	return output

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
