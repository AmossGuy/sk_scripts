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
	count = header_json["rows"][i]["entry_count"]
	
	if i == 2:
		for j in range(count):
			with open(f"{folder_path}/image {j} metadata.json", "r") as metadata_file:
				metadata_json = json.load(metadata_file)
			
			ltb_file.write(struct.pack(
				"<" + "I" * 19,
				metadata_json["unknown_a"],
				metadata_json["compression"],
				metadata_json["width"],
				metadata_json["height"],
				metadata_json["unknown_b"],
				metadata_json["unknown_c"],
				*metadata_json["palettes"],
				metadata_json["unknown_d"],
				os.path.getsize(f"{folder_path}/image {j}.wflz"),
			))
	elif i == 7:
		image_data_metapointer = ltb_file.tell()
		# again, we can only write pointers after the things they point to
		ltb_file.write(b"\0" * 8 * count)
		
		image_data_pointers = []
		for j in range(count):
			image_data_pointers.append(ltb_file.tell())
			with open(f"{folder_path}/image {j}.wflz", "rb") as wflz_data_file:
				ltb_file.write(wflz_data_file.read())
			
		ltb_file.write(struct.pack("<" + "Q" * count, *image_data_pointers))
		# no need to seek back since this is the last row
	else:
		with open(f"{folder_path}/row {i} data", "rb") as row_data_file:
			ltb_file.write(row_data_file.read())

ltb_file.seek(0)
ltb_file.write(struct.pack("<IIII", *header_json["start"]))
for i in range(8):
	row = header_json["rows"][i]
	ltb_file.write(struct.pack("<IIQ", row["mystery_number"], row["entry_count"], row_data_pointers[i]))

print(f"success! imploded into \"{ltb_file_path}\"")
