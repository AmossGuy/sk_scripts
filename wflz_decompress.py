#!/usr/bin/env python3

import io
import struct
import sys

WFLZ_BLOCK_SIZE = 4
WFLZ_MIN_MATCH_LEN = WFLZ_BLOCK_SIZE + 1

def wflz_decompress(reader):
	output = bytearray(b"")
	
	magic = reader.read(4)
	if magic == b"ZLFW":
		raise ValueError("chunked wflz format is not supported by this script")
	elif magic != b"WFLZ":
		raise ValueError("unknown magic. are you sure this is wflz data?")
	
	(compressed_size, decompressed_size) = struct.unpack("<II", reader.read(8))
	
	while True:
		block = reader.read(WFLZ_BLOCK_SIZE)
		if block == b"\0\0\0\0":
			break
		
		(backref_dist, backref_length, literal_count) = struct.unpack("<HBB", block)
		# kind of a gotcha
		if backref_length > 0:
			backref_length += WFLZ_MIN_MATCH_LEN - 1
			print(backref_dist, backref_length, literal_count)
		
		for i in range(backref_length):
			output.append(output[len(output) - backref_dist])
		
		literals = reader.read(literal_count)
		output.extend(literals)
	
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
