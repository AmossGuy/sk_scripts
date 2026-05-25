#!/usr/bin/env python3

import struct

with open("creation.ltb", "wb") as ltb_file:
	ltb_file.write(struct.pack("<IIII", 0, 0, 16, 16))
	for i in range(8):
		ltb_file.write(struct.pack("<IIQ", 0, 0, 0))

with open("creation.lvb", "wb") as lvb_file:
	for i in range(7):
		lvb_file.write(struct.pack("<IIQ", 0, 0, 0))
