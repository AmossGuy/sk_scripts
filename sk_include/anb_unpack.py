#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is a modified version of code from Shovel-Knight-Toolkit by leamsii, which can be found here:

https://github.com/leamsii/Shovel-Knight-Toolkit
"""

from sk_include.anbjson import ANBToJSON
from sk_include.hash_utils import load_wordlist, build_hash_map, resolve_hash
from sk_include.wflz import wflz_decompress
import sys

try:
    from PIL import Image
except:
    print("Error: Couldn't find the pillow library! Try running 'pip install pillow'")
    sys.exit(-1)

# Disable Pillow's decompression bomb check — ANB textures can be large
# but are trusted local data, not user-supplied images.
Image.MAX_IMAGE_PIXELS = None

import os
from pathlib import Path
import base64
import json

# Path to the wordlist used for resolving sequence hash names.
# Place wordlist.txt alongside this script, or adjust the path as needed.
WORDLIST_PATH = Path(__file__).parent / 'wordlist.txt'

class ANBUnpack:
    def __init__(self, filename):
        self.metadata = ANBToJSON(filename).metadata

        self.directory = Path(filename).parent / Path(filename).stem
        self.directory.mkdir(exist_ok=True)
        print(self.directory)

        frames = self.get_nodes(10, self.metadata['Node'], [])
        sequences = self.get_nodes(12, self.metadata['Node']['children'][0], [])

        print(f"Log: Unpacking {len(sequences)} Animation(s)..")

        # Load the wordlist once and build a hash->name lookup table.
        wordlist = load_wordlist(str(WORDLIST_PATH))
        if wordlist:
            print(f"Log: Loaded {len(wordlist)} words for hash resolution.")
        else:
            print("Log: No wordlist found — sequence directories will use raw numeric hash names.")
        hash_map = build_hash_map(wordlist)

        for sequence in sequences:
            raw_hash = sequence['body']['hash_name']
            resolved_name = resolve_hash(raw_hash, hash_map)

            if resolved_name:
                directory_name = resolved_name
                print(f"Log: Resolved hash {raw_hash} -> '{resolved_name}'")
            else:
                directory_name = str(raw_hash)

            directory_path = self.directory.joinpath(directory_name)
            directory_path.mkdir(exist_ok=True)

            # Store the resolved name back into metadata so pack can round-trip cleanly.
            sequence['body']['resolved_name'] = directory_name

            sequence_frames = self.get_nodes(11, sequence, [])
            for sequence_frame in sequence_frames:
                frame_index = sequence_frame['body']['frame']
                frame = frames[frame_index]
                texture = [n for n in frame['children'] if n['type'] == 1][0]
                vertex = [n for n in frame['children'] if n['type'] == 2][0]

                texture_width = texture['body']['width']
                texture_height = texture['body']['height']

                if texture_width == 0 or texture_height == 0:
                    print(f"Warning: frame_{frame_index} has zero texture dimensions "
                          f"({texture_width}x{texture_height}). Skipping.")
                    continue

                wflz_data = base64.b64decode(texture['body']['wflz']['body'])
                decompressed_data = wflz_decompress(wflz_data)

                image_output_path = Path(directory_path / f"frame_{str(frame_index)}.png")
                self.create_image(decompressed_data, image_output_path, texture_width, texture_height, vertex['body']['pieces'], frame_index)

        with open(self.directory.joinpath('metadata.json'), 'w') as file:
            json.dump(self.metadata, file)

        print("Log: Finished.")

    def get_nodes(self, node_type, node, nodes):
        if node['type'] == node_type:
            nodes.append(node)
        for _node in node['children']:
            self.get_nodes(node_type, _node, nodes)
        return nodes

    def create_image(self, data, output_path, frame_width, frame_height, vertices, frame_index):
        _buffer = data
        expected = frame_width * frame_height * 4

        if len(_buffer) < expected:
            actual_pixels = len(_buffer) // 4
            actual_side = int(actual_pixels ** 0.5)
            print(f"Warning: frame_{frame_index} buffer is {len(_buffer)} bytes "
                  f"({actual_pixels}px), expected {expected} ({frame_width}x{frame_height}x4). "
                  f"Closest square: ~{actual_side}x{actual_side}. Skipping.")
            os.remove(name)
            return

        image_out = Image.frombytes('RGBA', (frame_width, frame_height), _buffer, 'raw')
        final_image = Image.new("RGBA", (frame_width, frame_height))

        for vertex in vertices:
            texX = vertex["texX"]
            texY = vertex["texY"]
            piece_width = vertex["width"]
            piece_height = vertex["height"]

            # Clamp the crop region to the actual texture bounds.
            x1 = min(texX, frame_width)
            y1 = min(texY, frame_height)
            x2 = min(texX + piece_width, frame_width)
            y2 = min(texY + piece_height, frame_height)

            if x2 <= x1 or y2 <= y1:
                print(f"Warning: frame_{frame_index} vertex piece at ({texX},{texY}) "
                      f"size {piece_width}x{piece_height} is entirely outside "
                      f"texture bounds {frame_width}x{frame_height}, skipping piece.")
                continue

            if x2 < texX + piece_width or y2 < texY + piece_height:
                print(f"Warning: frame_{frame_index} vertex piece at ({texX},{texY}) "
                      f"size {piece_width}x{piece_height} extends outside "
                      f"texture bounds {frame_width}x{frame_height}, clamping.")

            region = (x1, y1, x2, y2)
            piece = image_out.crop(region)
            final_image.paste(piece, (x1, y1), piece)

        final_image.save(output_path)
