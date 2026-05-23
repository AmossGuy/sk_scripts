#!/usr/bin/env python3

import struct
import sys

if len(sys.argv) != 2:
	print("tool requires exactly one argument")
	sys.exit(1)

lvb_file = open(sys.argv[1], "rb")
header_json = {}

header_rows = []
for i in range(7):
	(mystery, count, pointer) = struct.unpack("<IIQ", lvb_file.read(16))
	header_rows.append({"mystery_number": mystery, "entry_count": count, "pointer": pointer})

OBJECT_PROPERTY_COUNT_ROW = 0
OBJECT_INFO_ROW = 1

lvb_file.seek(header_rows[OBJECT_INFO_ROW]["pointer"])
print("unkHash,layerNameHash,x,y,scalex,scaley,isUnk6,objectID,unk7,gID,propertyCount,propertyIndexStart,unk11")

for i in range(header_rows[OBJECT_INFO_ROW]["mystery_number"]):
	obj = struct.unpack("IIffffIHHIIII", lvb_file.read(0x30))
	print(",".join(map(str, obj)))
