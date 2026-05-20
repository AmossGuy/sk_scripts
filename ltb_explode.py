#!/usr/bin/env python3

import io
import json
import os
import struct
import sys

from PIL import Image
from wflz_decompress import wflz_decompress

row_entry_sizes = [
	32 + (4 * 24),
	4 * 5,
	4 * 19,
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

image_metadata = []

for i in range(8):
	ltb_file.seek(row_pointers[i])
	row_data = ltb_file.read(header_rows[i]["entry_count"] * row_entry_sizes[i])
	if i == 2: # image metadata
		for j in range(header_rows[i]["entry_count"]):
			raw_metadata = struct.unpack("<" + "I"*19, row_data[j*4*19 : j*4*19 + 4*19])
			image_metadata.append({
				"unknown_a": raw_metadata[0],
				"compression": raw_metadata[1],
				"width": raw_metadata[2],
				"height": raw_metadata[3],
				"unknown_b": raw_metadata[4],
				"unknown_c": raw_metadata[5],
				"palettes": raw_metadata[6:6+11],
				"unknown_d": raw_metadata[17],
				"data_size": raw_metadata[18],
			})
			
			with open(f"{explode_folder_path}/image {j} metadata.json", "w") as meta_write_file:
				json.dump(image_metadata[-1], meta_write_file)
	elif i == 7: # image data (wflz)
		for j in range(header_rows[i]["entry_count"]):
			(pointer,) = struct.unpack("<Q", row_data[j*8 : j*8 + 8])
			m = image_metadata[j]
			
			# seeking and reading here is fine because everything has already been read into row_data
			ltb_file.seek(pointer)
			wflz_data = ltb_file.read(m["data_size"])
			
			raw_image_data = wflz_decompress(io.BytesIO(wflz_data))
			image = Image.frombytes("RGBA", [m["width"], m["height"]], raw_image_data)
			image.save(f"{explode_folder_path}/image {j}.png")
	else:
		with open(f"{explode_folder_path}/row {i} data", "wb") as data_write_file:
			data_write_file.write(row_data)

print(f"success! exploded into \"{explode_folder_path}\"")
