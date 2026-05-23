#!/usr/bin/env python3

from pathlib import Path
import struct
import xml.etree.ElementTree as ET

print("note: very wip script")

folder_path = Path.home() / "Desktop/village_of_death.ltb exploded"

map_xml = ET.Element("map", orientation="orthogonal")

ET.SubElement(map_xml, "tileset", source="village_of_death.ltb exploded/image 0.tsx", firstgid=1)
ET.SubElement(map_xml, "tileset", source="village_of_death.ltb exploded/image 1.tsx", firstgid=785)

with open(folder_path / "row 3 data", "rb") as f:
	chunkmap_data = f.read()
with open(folder_path / "row 4 data", "rb") as f:
	tilemap_data = f.read()

with open(folder_path / "row 0 data", "rb") as f:
	for i in range(25): # number of layers hardcoded for now
		layer_name = f.read(0x20).split(b"\0")[0].decode("utf-8")
		layer_info = struct.unpack("<" + "I"*4*6, f.read(0x60))
		ET.SubElement(map_xml, "layer", name=layer_name)

tree = ET.ElementTree(map_xml)
tree.write(folder_path.parent / "tiled_test.tmx")
print("wrote the thing")
