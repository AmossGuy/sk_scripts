#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path
import sys

def format_heuristic(path):
	path = Path(path)
	header_json = (path / "header.json").exists()
	metadata_json = (path / "metadata.json").exists()
	match (header_json, metadata_json):
		case (True, False):
			return ".ltb"
		case (False, True):
			return ".anb"

parser = ArgumentParser(description="repacks the files extracted by sk_extract into their original formats")
parser.add_argument("folder")

args = parser.parse_args()
source_folder = Path(args.folder)

match format_heuristic(source_folder):
	case ".anb":
		print("detected format: anb")
		from sk_include.anb_pack import ANBPack
		ANBPack(source_folder)
	case ".ltb":
		print("detected format: ltb")
		from sk_include.ltb_implode import ltb_implode
		ltb_implode(source_folder)
	case _:
		print("the format detection heuristic failed. something is probably wrong with the folder you're trying to repack")
		sys.exit(1)
