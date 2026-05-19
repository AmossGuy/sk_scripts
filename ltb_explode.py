#!/usr/bin/env python3

import json
import os
import struct
import sys

row_entry_sizes = [
	32 + (4 * 7),
	4 * 5,
	4 * 6,
	4,
	2,
	8,
	4 * 5,
	8,
]

if len(sys.argv) != 2:
	print("tool requires exactly one argument: the ltb file path")
	print("a folder with the output is created adjacent to the ltb file")
	sys.exit(1)

ltb_file = open(sys.argv[1], "rb")
header_json = {}
header_json["start"] = struct.unpack("<IIII", ltb_file.read(16))

header_rows = []
row_pointers = []
for i in range(8):
	(mystery, count, pointer) = struct.unpack("<IIQ", ltb_file.read(16))
	header_rows.append({"mystery_number": mystery, "entry_count": count})
	row_pointers.append(pointer)

header_json["rows"] = header_rows

explode_folder_path = f"{sys.argv[1]} exploded"
if not os.path.exists(explode_folder_path):
	os.makedirs(explode_folder_path)

with open(f"{explode_folder_path}/header.json", "w") as header_json_file:
	json.dump(header_json, header_json_file)

for i in range(8):
	ltb_file.seek(row_pointers[i])
	row_data = ltb_file.read(header_rows[i]["entry_count"] * row_entry_sizes[i])
	with open(f"{explode_folder_path}/row {i} data", "wb") as data_write_file:
		data_write_file.write(row_data)

print(f"success! exploded into \"{explode_folder_path}\"")
