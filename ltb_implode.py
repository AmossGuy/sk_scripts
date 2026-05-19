#!/usr/bin/env python3

import json
import os
import struct
import sys

if len(sys.argv) != 2:
	print("tool requires exactly one argument: the exploded folder path")
	print("the ltb is created adjacent to this folder")
	sys.exit(1)

folder_path = sys.argv[1]

with open(f"{folder_path}/header.json") as header_file:
	header_json = json.load(header_file)

ltb_file_path = folder_path[0:folder_path.rindex(".ltb")] + ".ltb"
ltb_file = open(ltb_file_path, "wb")

# since the header contains pointers to everything we can't write it until we've placed the data
# here we reserve a placeholder to replace with the actual header later
ltb_file.write(b"\0" * 16 * 9)

row_data_pointers = []
for i in range(8):
	row_data_pointers.append(ltb_file.tell())
	
	if i == 2:
		pass # todo
	elif i == 7:
		pass # todo
	else:
		with open(f"{folder_path}/row {i} data", "rb") as row_data_file:
			ltb_file.write(row_data_file.read())

ltb_file.seek(0)
# todo: write actual header
