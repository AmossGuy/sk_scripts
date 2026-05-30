#!/usr/bin/env python3

from collections import namedtuple
import json
import struct
import sys

element_struct = struct.Struct("<32s64s64s32sIIIIIIIffffffffIIIIIII")
ElementInfo = namedtuple("ElementInfo", "identifier translated_text anb_path sprite_name ua1 ua2 ua3 ua4 ua5 ua6 global_index x_pos y_pos ub1 ub2 ub3 ub4 ub5 ub6 ub7 ub8 ub9 ub10 ub11 ub12 ub13")

if len(sys.argv) != 2:
	print("tool requires exactly one argument")
	sys.exit(1)

mnb_file = open(sys.argv[1], "rb")

(nothing_value, root_count, root_metapointer) = struct.unpack("<IIQ", mnb_file.read(16))

mnb_file.seek(root_metapointer)
root_pointers = struct.unpack("<"+"Q"*root_count, mnb_file.read(8*root_count))

mnb_json = {"nothing_value": nothing_value, "roots": []}
for pointer in root_pointers:
	mnb_file.seek(pointer)
	(root_id, element_count, root_unknown) = struct.unpack("<32sQQ", mnb_file.read(48))
	root_id = root_id.rstrip(b"\0").decode("utf-8")
	
	elements = []
	for i in range(element_count):
		element_info = ElementInfo(*element_struct.unpack_from(mnb_file.read(280)))
		element_info = element_info._asdict()
		for key in ["identifier", "translated_text", "anb_path", "sprite_name"]:
			element_info[key] = element_info[key].rstrip(b"\0").decode("utf-8")
		elements.append(element_info)
	
	mnb_json["roots"].append({"root_identifier": root_id, "unknown": root_unknown, "elements": elements})

print(json.dumps(mnb_json, indent=2))
