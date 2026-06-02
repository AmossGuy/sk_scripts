#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path

parser = ArgumentParser(description="extracts various file formats used by Shovel Knight into editable forms")
parser.add_argument("filename")

args = parser.parse_args()
source_filename = Path(args.filename)

match source_filename.suffix:
	case ".anb":
		from sk_include.anb_unpack import ANBUnpack
		ANBUnpack(source_filename)
	case ".ltb":
		from sk_include.ltb_explode import ltb_explode
		ltb_explode(source_filename)
	case _:
		print("unknown file extension. this script relies on file extensions to identify file type")
		sys.exit(1)
