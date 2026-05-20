#!/usr/bin/env python3

import io
import struct

WFLZ_HEADER_SIZE = 4 * 3
WFLZ_BLOCK_SIZE = 4

WFLZ_MIN_MATCH_LEN = WFLZ_BLOCK_SIZE + 1
WFLZ_MAX_LITERALS = 0xFF

def wlfz_hashptr(x):
	# the original wflz source uses some fancy macros to calculate that 16, but in the end it's just a constant
	return ((x * 2654435761) & 0xFF_FF_FF_FF) >> 16

def wlfz_compress(data):
	writer = io.BytesIO()
	
	# reserve space for header. we won't actually write it until we're finished compressing and know the compressed size
	writer.write(b"\xFF" * WFLZ_HEADER_SIZE)
	
	read_pos = 0
	wflz_dict = b"\0" * 0xFFFF
	block_literals = bytearray(b"")
	
	# firstly: the first WFLZ_MIN_MATCH_LEN bytes of the data are always written as literals
	for _ in range(min(WFLZ_MIN_MATCH_LEN, len(data))):
		if len(data) - read_pos >= 4:
			pass # TODO: add to dict
		block_literals.append(data[read_pos])
		read_pos += 1
	writer.write(struct.pack("<HBB", 0, 0, len(block_literals)))
	writer.write(block_literals)
	block_literals = bytearray(b"")
	
	# TODO: main loop
	# writer.write(struct.pack("<HBB", ))
	
	# final literals
	while read_pos < len(data):
		if len(block_literals) == WFLZ_MAX_LITERALS:
			writer.write(struct.pack("<HBB", 0, 0, len(block_literals)))
			writer.write(block_literals)
			block_literals = bytearray(b"")
		block_literals.append(data[read_pos])
		read_pos += 1
	writer.write(struct.pack("<HBB", 0, 0, len(block_literals)))
	writer.write(block_literals) # no need to erase it this time since we're already done
	
	# add terminator block
	writer.write(b"\0" * WFLZ_BLOCK_SIZE)
	
	# write the actual header
	writer.seek(0)
	writer.write(b"WFLZ")
	compressed_size = len(writer.getbuffer()) - (WFLZ_HEADER_SIZE + WFLZ_BLOCK_SIZE)
	writer.write(struct.pack("<II", compressed_size, len(data)))
	
	compressed_data = writer.getvalue()
	writer.close()
	return compressed_data

if __name__ == "__main__":
	print(wlfz_compress(b"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer purus elit, vulputate sed vehicula quis, lobortis nec velit. Etiam blandit non est at laoreet. Praesent eleifend dignissim lacus, a auctor tortor dignissim sit amet. In ut ornare diam, ut molestie nisl. Suspendisse in elementum lorem, ut ullamcorper ipsum. Quisque libero leo, ultricies at maximus non, pellentesque non erat. Praesent convallis tincidunt mollis."))
