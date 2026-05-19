#!/usr/bin/env python3

import io

WFLZ_BLOCK_SIZE = 4
WFLZ_MIN_MATCH_LEN = WFLZ_BLOCK_SIZE + 1

def wlfz_hashptr(x):
	# the original wflz source uses some fancy macros to calculate that 16, but in the end it's just a constant
	return ((x * 2654435761) & 0xFF_FF_FF_FF) >> 16

def wlfz_compress(data):
	writer = io.BytesIO()
	
	# reserve space for header. we won't actually write it until we're finished compressing and know the compressed size
	writer.write(b"\0" * 4 * 3)
	
	num_literals = 0
	wflz_dict = b"\0" * 0xFFFF
	
	# firstly: the first WFLZ_MIN_MATCH_LEN bytes of the data are always written as literals
	for i in range(min(WFLZ_MIN_MATCH_LEN, len(data))):
		if len(data) - i >= 4:
			pass
		writer.write(data[i].to_bytes(1))
	
	return writer.getvalue()

if __name__ == "__main__":
	print(wlfz_compress(b"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer purus elit, vulputate sed vehicula quis, lobortis nec velit. Etiam blandit non est at laoreet. Praesent eleifend dignissim lacus, a auctor tortor dignissim sit amet. In ut ornare diam, ut molestie nisl. Suspendisse in elementum lorem, ut ullamcorper ipsum. Quisque libero leo, ultricies at maximus non, pellentesque non erat. Praesent convallis tincidunt mollis."))
