import io
import struct

WFLZ_HEADER_SIZE = 4 * 3
WFLZ_BLOCK_SIZE = 4

WFLZ_MAX_MATCH_DIST = 0xFFFF
WFLZ_MIN_MATCH_LEN = WFLZ_BLOCK_SIZE + 1
WFLZ_MAX_MATCH_LEN = 0xFF - 1 + WFLZ_MIN_MATCH_LEN
WFLZ_MAX_LITERALS = 0xFF

def wflz_hash(b):
	assert len(b) == 4
	x = (int.from_bytes(b, "little"))
	# the original wflz source uses some fancy macros to calculate that 16, but in the end it's just a constant
	return ((x * 2654435761) & 0xFF_FF_FF_FF) >> 16

# called wfLZ_MemCmp in the original
# "returns the number of sequential matching characters"
def wflz_compare(data, start_a, start_b, max_len):
	matched = 0
	while matched < max_len and data[start_a + matched] == data[start_b + matched]:
		matched += 1
	return matched

class WflzBlock:
	def __init__(self):
		self.backref_dist = 0
		self.backref_length = 0
		self.literals = bytearray(b"")
	
	def write_to(self, writer):
		writer.write(struct.pack("<HBB", self.backref_dist, self.backref_length, len(self.literals)))
		writer.write(self.literals)

def wflz_compress(data):
	writer = io.BytesIO()
	
	# reserve space for header. we won't actually write it until we're finished compressing and know the compressed size
	writer.write(b"\xFF" * WFLZ_HEADER_SIZE)
	
	# hash table, with a starring role in this compression scheme
	# sequences of 4 bytes are turned into a 32-bit integer and hashed with wflz_hash; that hash is used as an index into this table
	# the values of this table are indexes into the data, pointing to where those bytes sequences can be found
	wflz_dict = [None] * 0xFFFF
	
	block = WflzBlock()
	read_pos = 0
	
	# firstly: the first WFLZ_MIN_MATCH_LEN bytes of the data are always written as literals
	for _ in range(min(WFLZ_MIN_MATCH_LEN, len(data))):
		if len(data) - read_pos >= 4:
			whash = wflz_hash(data[read_pos:read_pos+4])
			wflz_dict[whash] = read_pos
		block.literals.append(data[read_pos])
		read_pos += 1
	
	# main loop
	while len(data) - read_pos >= WFLZ_MIN_MATCH_LEN:
		whash = wflz_hash(data[read_pos:read_pos+4])
		match_pos = wflz_dict[whash]
		window_start = read_pos - WFLZ_MAX_MATCH_DIST
		match_length = 0
		max_match_len = min(WFLZ_MAX_MATCH_LEN, (len(data) - read_pos))
		
		wflz_dict[whash] = read_pos
		
		# "a match was found, ensure it really is a match and not a hash collision, and determine its length"
		if match_pos != None and match_pos >= window_start:
			match_length = wflz_compare(data, read_pos, match_pos, max_match_len)
		
		if match_length >= WFLZ_MIN_MATCH_LEN:
			match_dist = read_pos - match_pos
			
			block.write_to(writer)
			block = WflzBlock()
			read_pos += match_length
			
			block.backref_dist = match_dist
			block.backref_length = match_length - WFLZ_MIN_MATCH_LEN + 1
		# "output a literal byte: no entries for this position found, entry is too far away, entry was a hash collision, or the entry did not meet the minimum match length"
		else:
			# "if we've hit the max number of sequential literals, we need to output a compression block header"
			if len(block.literals) == WFLZ_MAX_LITERALS:
				block.write_to(writer)
				block = WflzBlock()
			
			block.literals.append(data[read_pos])
			read_pos += 1
	
	# final literals
	while read_pos < len(data):
		if len(block.literals) == WFLZ_MAX_LITERALS:
			block.write_to(writer)
			block = WflzBlock()
		block.literals.append(data[read_pos])
		read_pos += 1
	block.write_to(writer) # no need for a new block this time since we're already done
	
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

def wflz_decompress(reader):
	output = bytearray(b"")
	
	magic = reader.read(4)
	if magic == b"ZLFW":
		raise ValueError("chunked wflz format is not supported by this script")
	elif magic != b"WFLZ":
		raise ValueError("unknown magic. are you sure this is wflz data?")
	
	(compressed_size, decompressed_size) = struct.unpack("<II", reader.read(8))
	
	while True:
		block = reader.read(WFLZ_BLOCK_SIZE)
		if block == b"\0\0\0\0":
			break
		
		(backref_dist, backref_length, literal_count) = struct.unpack("<HBB", block)
		# kind of a gotcha
		if backref_length > 0:
			backref_length += WFLZ_MIN_MATCH_LEN - 1
		
		for i in range(backref_length):
			output.append(output[len(output) - backref_dist])
		
		literals = reader.read(literal_count)
		output.extend(literals)
	
	return output
