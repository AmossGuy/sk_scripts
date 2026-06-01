#!/usr/bin/env python3

from collections import namedtuple
import csv
import io
import json
import os
from pathlib import Path
import struct

from PIL import Image
from sk_include.wflz import wflz_decompress

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

def explode_layer_headers(folder_path, fi, count):
	LayerInfo = namedtuple("LayerInfo", "name nameHash unk1 unk2 cameraMultX unk3 cameraMultY unk4 unk5 unk6 unkI7 unkI8 unkI9 vertexBufferInfoIndex isUsingStaticVertexBuffer unkI10 chunkXCount chunkYCount chunkIDStart offsetX offsetY startX startY endX endY")
	
	layers = []
	for i in range(count):
		layer_info = LayerInfo(*struct.unpack("<32sIffffffffIIIIIIIIIffIIII", fi.read(0x80)))
		layer_info = layer_info._asdict()
		layer_info["name"] = layer_info["name"].split(b"\0")[0].decode()
		layers.append(layer_info)
	
	with open(Path(folder_path) / "layers.json", "w") as json_file:
		json.dump(layers, json_file, indent="\t")
	return layers

def explode_layer_chunkmaps(folder_path, data, layers):
	layer_folder = Path(folder_path) / "layers"
	layer_folder.mkdir(exist_ok=True)
	offset_str = lambda s: "" if s == 0 else f"offset_{s}"
	
	seeker = io.BytesIO(data)
	for layer in layers:
		structformat = "<" + "I" * layer["chunkXCount"]
		structsize = struct.calcsize(structformat)
		
		seeker.seek(layer["chunkIDStart"] * 4)
		with open(layer_folder / f"{layer['name']}.csv", "w", newline="") as csvfile:
			writer = csv.writer(csvfile)
			for row_n in range(layer["chunkYCount"]):
				row_values = struct.unpack(structformat, seeker.read(structsize))
				writer.writerow(map(offset_str, row_values))

CHUNK_SIZE = 16
CHUNK_BYTES = CHUNK_SIZE * CHUNK_SIZE * 2

def explode_chunk_tilemaps(folder_path, fi, data_length):
	fi.read(2) # ignore initial padding
	chunk_folder = Path(folder_path) / "chunks"
	chunk_folder.mkdir(exist_ok=True)
	structformat = "<" + "H" * CHUNK_SIZE
	
	offset = 2
	while (offset + CHUNK_BYTES) <= data_length:
		chunk_data = fi.read(CHUNK_BYTES)
		
		with open(chunk_folder / f"offset_{offset // 2}.csv", "w", newline="") as csvfile:
			writer = csv.writer(csvfile)
			for i, row_values in enumerate(struct.iter_unpack(structformat, chunk_data)):
				writer.writerow(map(tile_string, row_values))
		
		offset += CHUNK_BYTES

def tile_string(raw):
	string = str(raw & 0xFFF)
	if raw & 0x1000: string += "p" # second tileset page
	if raw & 0x2000: string += "h" # horizontal flip
	if raw & 0x4000: string += "v" # vertical flip
	if raw & 0x8000: string += "s" # solid tile?
	return string

def ltb_explode(ltb_path):
	ltb_path = Path(ltb_path)
	explode_folder_path = ltb_path.with_stem(f"{ltb_path.stem} exploded")
	os.makedirs(explode_folder_path, exist_ok=True)
	with open(ltb_path, "rb") as ltb_file:
		ltb_explode_from_reader(ltb_file, explode_folder_path)

def ltb_explode_from_reader(ltb_file, explode_folder_path):
	header_json = {}
	header_json["start"] = struct.unpack("<IIII", ltb_file.read(16))

	header_rows = []
	row_pointers = []
	for i in range(8):
		(mystery, count, pointer) = struct.unpack("<IIQ", ltb_file.read(16))
		header_rows.append({"mystery_number": mystery, "entry_count": count})
		row_pointers.append(pointer)

	header_json["rows"] = header_rows

	with open(f"{explode_folder_path}/header.json", "w") as header_json_file:
		json.dump(header_json, header_json_file)

	image_metadata = []

	for i in range(8):
		ltb_file.seek(row_pointers[i])
		row_data = ltb_file.read(header_rows[i]["entry_count"] * row_entry_sizes[i])
		if i == 0:
			exploded_layers = explode_layer_headers(explode_folder_path, io.BytesIO(row_data), header_rows[i]["entry_count"])
		elif i == 2: # image metadata
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
				
				clean_metadata = image_metadata[-1].copy()
				# the values being deleted here are stuff that can be reconstructed from a png
				del clean_metadata["width"]
				del clean_metadata["height"]
				del clean_metadata["data_size"]
				
				with open(f"{explode_folder_path}/image {j} metadata.json", "w") as meta_write_file:
					json.dump(clean_metadata, meta_write_file)
		elif i == 3:
			explode_layer_chunkmaps(explode_folder_path, row_data, exploded_layers)
		elif i == 4:
			explode_chunk_tilemaps(explode_folder_path, io.BytesIO(row_data), len(row_data))
		elif i == 7: # image data (wflz)
			for j in range(header_rows[i]["entry_count"]):
				(pointer,) = struct.unpack("<Q", row_data[j*8 : j*8 + 8])
				m = image_metadata[j]
				
				# seeking and reading here is fine because everything has already been read into row_data
				ltb_file.seek(pointer)
				image_data = ltb_file.read(m["data_size"])
				
				if m["compression"] != 0:
					image_data = wflz_decompress(image_data)
				image_mode = "RGBA" if m["palettes"][0] == 0xFF_FF_FF_FF else "L"
				
				image = Image.frombytes(image_mode, [m["width"], m["height"]], image_data)
				image.save(f"{explode_folder_path}/image {j}.png")
		else:
			with open(f"{explode_folder_path}/row {i} data", "wb") as data_write_file:
				data_write_file.write(row_data)
	
	print(f"success! exploded into \"{explode_folder_path}\"")
