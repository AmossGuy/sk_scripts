#!/usr/bin/env python3

from collections import namedtuple
import csv
import json
import os
from pathlib import Path
import re
import struct
import sys

from PIL import Image
from wflz_compress import wflz_compress

def ensure_alignment(f):
	pos = f.tell()
	if (pos % 8) != 0:
		f.write(b"\0" * (8 - (pos % 8)))

tile_encode_regex = re.compile("^([0-9]+)([a-zA-Z]*)$")

def tile_encode(s):
	match = tile_encode_regex.match(s)
	tile_index = int(match.group(1))
	flag_string = match.group(2).lower()
	
	n = tile_index & 0xFFF
	if "p" in flag_string: n |= 0x1000
	if "h" in flag_string: n |= 0x2000
	if "v" in flag_string: n |= 0x4000
	if "s" in flag_string: n |= 0x8000
	return n

CHUNK_SIZE = 16
CHUNK_BYTES = CHUNK_SIZE * CHUNK_SIZE * 2

class TilemapBuilder:
	def __init__(self, folder_path):
		self.folder_path = folder_path
		self.chunk_data = bytearray(b"\0\0")
		self.chunk_dict = {}
		self.layer_data = bytearray(b"")
		self.layer_dict = {}
	
	def load_chunk(self, name):
		if name not in self.chunk_dict:
			pointer = len(self.chunk_data)
			self.chunk_dict[name] = pointer
			with open(Path(self.folder_path) / "chunks" / f"{name}.csv", "r", newline="") as csvfile:
				reader = csv.reader(csvfile)
				for row in reader:
					row_data = struct.pack("<" + "H" * CHUNK_SIZE, *map(tile_encode, row))
					self.chunk_data.extend(row_data)
		return self.chunk_dict[name]
	
	def load_layer(self, name):
		layer_pointer = len(self.layer_data) // 4
		with open(Path(self.folder_path) / "layers" / f"{name}.csv", "r", newline="") as csvfile:
			reader = csv.reader(csvfile)
			for row in reader:
				for chunk_name in row:
					if chunk_name == "":
						self.layer_data.extend(struct.pack("<I", 0))
					else:
						self.layer_data.extend(struct.pack("<I", self.load_chunk(chunk_name)))
		return layer_pointer

def implode_layer_headers(folder_path, writer, json_layers):
	LayerInfo = namedtuple("LayerInfo", "name nameHash unk1 unk2 cameraMultX unk3 cameraMultY unk4 unk5 unk6 unkI7 unkI8 unkI9 vertexBufferInfoIndex isUsingStaticVertexBuffer unkI10 chunkXCount chunkYCount chunkIDStart offsetX offsetY startX startY endX endY")
	
	for layer in json_layers:
		layer["name"] = layer["name"].encode()
		layer_tuple = LayerInfo(**layer)
		writer.write(struct.pack("<32sIffffffffIIIIIIIIIffIIII", *layer_tuple))

if len(sys.argv) != 2:
	print("tool requires exactly one argument: the exploded folder path")
	print("the ltb is created adjacent to this folder")
	sys.exit(1)

folder_path = sys.argv[1]

with open(f"{folder_path}/header.json") as header_file:
	header_json = json.load(header_file)

ltb_file_path = folder_path[0:folder_path.rindex(".ltb")] + " imploded.ltb"
ltb_file = open(ltb_file_path, "wb")

# since the header contains pointers to everything we can't write it until we've placed the data
# here we reserve a placeholder to replace with the actual header later
ltb_file.write(b"\0" * 16 * 9)

# tilemap is a bit complicated and needs to be sorted out before the layer headers so we have the pointers by then
with open(Path(folder_path) / "layers.json", "r") as json_file:
	json_layers = json.load(json_file)
tilemap_builder = TilemapBuilder(folder_path)
for layer in json_layers:
	layer_pointer = tilemap_builder.load_layer(layer["name"])
	layer["chunkIDStart"] = layer_pointer

row_data_pointers = []
images = [] # we put all the image data in here at once. not optimal memory use? whatever
for i in range(8):
	row_data_pointers.append(ltb_file.tell())
	count = header_json["rows"][i]["entry_count"]
	
	if i == 0:
		implode_layer_headers(folder_path, ltb_file, json_layers)
		# TODO: adjust header for different numbers of layers
		# len(json_layers)
	elif i == 2:
		for j in range(count):
			with open(f"{folder_path}/image {j} metadata.json", "r") as metadata_file:
				metadata_json = json.load(metadata_file)
			
			image = Image.open(f"{folder_path}/image {j}.png")
			correct_image_mode = "RGBA" if metadata_json["palettes"][0] == 0xFF_FF_FF_FF else "L"
			if image.mode != correct_image_mode:
				raise ValueError(f"image {j} has the wrong pixel format")
			
			image_data = image.tobytes()
			if metadata_json["compression"] != 0:
				image_data = wflz_compress(image_data)
			images.append(image_data)
			
			ltb_file.write(struct.pack(
				"<" + "I" * 19,
				metadata_json["unknown_a"],
				metadata_json["compression"],
				image.size[0],
				image.size[1],
				metadata_json["unknown_b"],
				metadata_json["unknown_c"],
				*metadata_json["palettes"],
				metadata_json["unknown_d"],
				len(image_data),
			))
	elif i == 3:
		ltb_file.write(tilemap_builder.layer_data)
	elif i == 4:
		ltb_file.write(tilemap_builder.chunk_data)
	elif i == 7:
		image_data_metapointer = ltb_file.tell()
		# again, we can only write pointers after the things they point to
		ltb_file.write(b"\0" * 8 * count)
		
		image_data_pointers = []
		for j in range(count):
			image_data_pointers.append(ltb_file.tell())
			ltb_file.write(images[j])
		
		ltb_file.seek(image_data_metapointer)
		ltb_file.write(struct.pack("<" + "Q" * count, *image_data_pointers))
		# no need to seek back since this is the last row
	else:
		with open(f"{folder_path}/row {i} data", "rb") as row_data_file:
			ltb_file.write(row_data_file.read())
	
	ensure_alignment(ltb_file)

ltb_file.seek(0)
ltb_file.write(struct.pack("<IIII", *header_json["start"]))
for i in range(8):
	row = header_json["rows"][i]
	ltb_file.write(struct.pack("<IIQ", row["mystery_number"], row["entry_count"], row_data_pointers[i]))

print(f"success! imploded into \"{ltb_file_path}\"")
