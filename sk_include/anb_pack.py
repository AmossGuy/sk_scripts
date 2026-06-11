#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is a modified version of code from Shovel-Knight-Toolkit by leamsii, which can be found here:

https://github.com/leamsii/Shovel-Knight-Toolkit
"""

import sys
try:
    from PIL import Image
except:
    print("Error: Couldn't find the pillow library! Try running 'pip install pillow'")
    sys.exit(-1)

import os
import struct
from pathlib import Path
import glob
import json
import base64
from sk_include.hash_utils import compute_hash
from sk_include.wflz import wflz_compress

NodeTypeName = {
    0 : 'Node',
    1 : 'Texture',
    2 : 'Vertex',
    3 : 'Meta',
    4 : 'MetaScalar',
    5 : 'MetaPoint',
    6 : 'MetaAnchor',
    7 : 'MetaRect',
    8 : 'MetaString',
    9 : 'MetaTable',
    10 : 'Frame',
    11 : 'SequenceFrame',
    12 : 'Sequence',
    13 : 'Animation'
}
NodeStructureSize = {
    'Node': 24,
    'Texture': 24,
    'Vertex': 16,
    'MetaScalar': 8,
    'MetaPoint': 16,
    'MetaAnchor': 16,
    'MetaRect': 32,
    'MetaString': 16,
    'MetaTable': 8,
    'Frame': 16,
    'SequenceFrame': 8,
    'Sequence': 8,
    'Animation': 24,
}
TraversedNodes = {}

def folder_name_to_hash(name: str) -> int:
    """Convert a sequence folder name to its numeric hash.

    If the folder name is already a plain integer (i.e. the hash was never
    resolved during unpack) it is returned as-is.  Otherwise the name is
    hashed with lookup3 hashlittle so it matches the value stored in the
    Sequence node's hash_name field.
    """
    if name.isdigit():
        return int(name)
    return compute_hash(name)

class ANBPack:
    def __init__(self, folder):
        self.directory = Path(folder)
        metadata_dir = self.directory.joinpath('metadata.json')
        self.metadata = json.loads(metadata_dir.read_text())
        self.hash_chunk = b''

        os.chdir(self.directory)
        sequence_dirs = [d for d in glob.glob('*') if Path(d).is_dir()]
        frames = self.get_nodes(10, self.metadata['Node'], [])
        sequences = {}
        old_sequences = self.get_nodes(12, self.metadata['Node']['children'][0], [])
        print(f"Log: Packing {len(old_sequences)} Animation(s)..")
        new_image_sizes = {}

        # Build a lookup from numeric hash → sequence folder path so we can
        # match resolved (plain-text) folder names back to their Sequence nodes.
        dir_hash_map = {folder_name_to_hash(d): d for d in sequence_dirs}

        self.initialize_pointer_write_stuff()

        for sequence_dir in sequence_dirs:
            sequences[sequence_dir] = {}
            sequences_path = Path(self.directory.joinpath(sequence_dir))
            os.chdir(sequences_path)

            for image in glob.glob("*.png"):
                (width, height) = Image.open(image).size
                new_image_sizes[image] = {"width": width, "height": height}
                compressed_image_path = sequences_path.joinpath(image)
                compressed_wflz = self.compress_image(compressed_image_path)
                sequences[sequence_dir][Path(image).stem] = compressed_wflz

        for sequence in old_sequences:
            raw_hash = sequence['body']['hash_name']

            # Find which folder on disk corresponds to this Sequence node.
            # It may be stored as the resolved plain-text name or as the raw
            # numeric hash string — dir_hash_map handles both cases.
            matched_dir = dir_hash_map.get(raw_hash)
            if matched_dir is None:
                print(f"Warning: No folder found for sequence hash {raw_hash}, skipping.")
                continue

            for sequence_frame in self.get_nodes(11, sequence, []):
                frame_index = sequence_frame['body']['frame']

                frame = frames[frame_index]
                texture = [n for n in frame['children'] if n['type'] == 1][0]

                wflz_data = sequences[matched_dir][f"frame_{frame_index}"]

                # we're not writing these right now so we can't set the pointer target just yet
                texture['body']['wflz']['size'] = len(wflz_data)
                texture['body']['wflz']['body'] = wflz_data + bytes((self.align(len(wflz_data), 8) - len(wflz_data)))

        with open(self.directory.joinpath(self.directory.name + '.anb'), 'wb') as file:
            header = self.metadata['file_header']

            file.write(b'YCSN')
            file.write(struct.pack('<IIIQ', header["fixup"], header["version"], header["pad1"], header["pad2"]))

            node = self.metadata['Node']
            file.write(struct.pack('<II8s', node["type"], len(node["children"]), b"\xDE\xAD\xBE\xEF\x01\0\0\0"))
            self.set_pointer_source(node["children"], file.tell() - 8)

            self.traverse(file, node['children'][0], node)

            self.hash_chunk_pointer = file.tell()
            file.write(self.hash_chunk)

            for node in self.get_nodes([1, 2], self.metadata['Node']['children'][0], []):
                if node["type"] == 1: # texture
                    self.set_pointer_target(node["body"]["wflz"], file.tell())
                    file.write(struct.pack('<I', node['body']['wflz']['flag']))
                    file.write(struct.pack('<I', node['body']['wflz']['size']))
                    file.write(node['body']['wflz']['body'])
                elif node["type"] == 2: # vertex
                    self.set_pointer_target(node["body"]["pieces"], file.tell())
                    vertex_chunk = self.build_vertex_chunk(node)
                    file.write(vertex_chunk)

            self.do_pointer_writes(file)

        print("Log: Finished.")

    def align(self, v: int, m: int):
        mask = m - 1
        return (v + mask) & ~mask

    def get_nodes(self, node_type, node, nodes):
        if not isinstance(node_type, (list, tuple)):
            node_type = [node_type]

        if node['type'] in node_type:
            nodes.append(node)
        for _node in node['children']:
            self.get_nodes(node_type, _node, nodes)
        return nodes

    def build_vertex_chunk(self, vertex):
        vertex_chunk = b''
        vertex_chunk += struct.pack('<I', vertex["body"]["hash_flag"])
        vertex_chunk += struct.pack('<I', vertex["body"]["hash_size"])

        for piece in vertex["body"]["pieces"]:
            vertex_chunk += struct.pack('<f', piece["posX"])
            vertex_chunk += struct.pack('<f', piece["posY"])
            vertex_chunk += struct.pack('<H', piece["texX"])
            vertex_chunk += struct.pack('<H', piece["texY"])
            vertex_chunk += struct.pack('<H', piece["width"])
            vertex_chunk += struct.pack('<H', piece["height"])

        return vertex_chunk

    def traverse(self, file, node, parent):
        self.unpack_node(node, file, parent)

        TraversedNodes[NodeTypeName[parent['type']]] = TraversedNodes.get(NodeTypeName[parent["type"]], 0) + 1
        if TraversedNodes[NodeTypeName[parent["type"]]] >= len(parent["children"]):
            TraversedNodes[NodeTypeName[parent["type"]]] = 0
            self.set_pointer_target(parent["children"], file.tell())
            for child in parent['children']:
                # file.write(struct.pack('<Q', child['offset']))
                file.write(b"\xDE\xAD\xBE\xEF\x02\0\0\0")
                self.set_pointer_source(child, file.tell() - 8)

        for _node in node['children']:
            self.traverse(file, _node, node)

    def compress_image(self, image_name):
        _image = Image.open(image_name)
        padded_image = _image

        width, height = padded_image.size
        pixels = list(padded_image.getdata())
        pixels = [pixels[i * width:(i + 1) * width] for i in range(height)]
        compression_size = width * height * 4

        data = bytearray()
        for row in pixels:
            for r, g, b, a in row:
                data.extend(struct.pack('<BBBB', r, g, b, a))

        return wflz_compress(data)

    def get_padded_image(self, width, height, image):
        new_width = self.align_image(width, 8)
        new_height = self.align_image(height, 8)
        padding_top = new_height - height
        new_image = Image.new("RGBA", (new_width, new_height))
        new_image.paste(image, (0, padding_top))
        return new_image

    def align_image(self, v: int, m: int):
        mask = m - 1
        aligned_value = (v + mask) & ~mask
        if aligned_value < v:
            aligned_value += m
        return aligned_value

    def unpack_node(self, node, file, parent):
        _type = NodeTypeName[node['type']]

        file_tell = file.tell()
        node['offset'] = file_tell
        self.set_pointer_target(node, file_tell)
        if len(node["children"]) == 0:
            node_chunk_body = struct.pack('<IIQ', node["type"], 0, 0)
        else:
            node_chunk_body = struct.pack('<II8s', node["type"], len(node["children"]), b"\xDE\xAD\xBE\xEF\x03\0\0\0")
            self.set_pointer_source(node["children"], file_tell + 8) # plus 8 because node_chunk_body hasn't been written yet!!!

        if _type == 'Texture':
            node_chunk_body += struct.pack('<I', node["body"]["width"])
            node_chunk_body += struct.pack('<I', node["body"]["height"])
            node_chunk_body += struct.pack('<I', node["body"]["flags"])
            node_chunk_body += struct.pack('<I', node["body"]["padding"])

            self.set_pointer_source(node["body"]["wflz"], file_tell + len(node_chunk_body))
            node_chunk_body += b"\xDE\xAD\xBE\xEF\x04\0\0\0"

        if _type == 'Vertex':
            node_chunk_body += struct.pack('<I', node["body"]["num_verts"])
            node_chunk_body += struct.pack('<I', node["body"]["flags"])

            parent_texture = [n for n in parent['children'] if n['type'] == 1][0]
            parent_vertex = [n for n in parent['children'] if n['type'] == 2][0]

            self.set_pointer_source(node["body"]["pieces"], file_tell + len(node_chunk_body))
            node_chunk_body += b"\xDE\xAD\xBE\xEF\x05\0\0\0"

        if _type == 'MetaPoint':
            node_chunk_body += struct.pack('<f', node["body"]["x"])
            node_chunk_body += struct.pack('<f', node["body"]["y"])
            node_chunk_body += struct.pack('<f', node["body"]["z"])
            node_chunk_body += struct.pack('<I', node["body"]["padding"])

        if _type == 'MetaAnchor':
            node_chunk_body += struct.pack('<f', node["body"]["x"])
            node_chunk_body += struct.pack('<f', node["body"]["y"])
            node_chunk_body += struct.pack('<f', node["body"]["z"])
            node_chunk_body += struct.pack('<f', node["body"]["angle"])

        if _type == 'MetaRect':
            node_chunk_body += struct.pack('<f', node["body"]["centerx"])
            node_chunk_body += struct.pack('<f', node["body"]["centery"])
            node_chunk_body += struct.pack('<f', node["body"]["centerz"])
            node_chunk_body += struct.pack('<f', node["body"]["extentsx"])
            node_chunk_body += struct.pack('<f', node["body"]["extentsy"])
            node_chunk_body += struct.pack('<f', node["body"]["extentsz"])
            node_chunk_body += struct.pack('<f', node["body"]["anglex"])
            node_chunk_body += struct.pack('<I', node["body"]["padding"])

        if _type == 'MetaString':
            node_chunk_body += struct.pack('<I', node["body"]["str_length"])
            node_chunk_body += struct.pack('<I', node["body"]["padding"])

            self.set_pointer_source(node["body"]["string"], file_tell + len(node_chunk_body))
            node_chunk_body += b"\xDE\xAD\xBE\xEF\x06\0\0\0"

            self.set_pointer_target(node["body"]["string"], len(self.hash_chunk), relative_to_hash_chunk=True)
            self.hash_chunk += struct.pack('<I', node["body"]["string_flag"])
            self.hash_chunk += struct.pack('<I', node["body"]["string_size"])
            hash = node["body"]["string"].encode('utf-8')
            self.hash_chunk += hash + bytes(self.align(node["body"]["string_size"], 8) - node["body"]["string_size"])

        if _type == 'MetaTable':
            hashname_pointer = node['body']['hashname_pointer']
            if hashname_pointer != 0:
                self.set_pointer_source(node["body"]["hash"], file_tell + len(node_chunk_body))
                node_chunk_body += b"\xDE\xAD\xBE\xEF\x07\0\0\0"

                self.set_pointer_target(node["body"]["hash"], len(self.hash_chunk), relative_to_hash_chunk=True)
                self.hash_chunk += struct.pack('<I', node["body"]["hash_flag"])
                self.hash_chunk += struct.pack('<I', node["body"]["hash_size"])

                hash = base64.b64decode(node["body"]["hash"])
                self.hash_chunk += hash + bytes(self.align(len(hash), 8) - len(hash))
            else:
                node_chunk_body += bytes(8)

        if _type == 'SequenceFrame':
            node_chunk_body += struct.pack('<I', node["body"]["frame"])
            node_chunk_body += struct.pack('<f', node["body"]["delay"])

        if _type == 'Sequence':
            node_chunk_body += struct.pack('<I', node["body"]["hash_name"])
            node_chunk_body += struct.pack('<I', node["body"]["frame_count"])

        if _type == 'Animation':
            node_chunk_body += struct.pack('<I', node["body"]["sequence_count"])
            node_chunk_body += struct.pack('<I', node["body"]["frame_count"])
            node_chunk_body += struct.pack('<I', node["body"]["single_texture"])
            node_chunk_body += struct.pack('<I', node["body"]["palette_index"])

            self.set_pointer_source(node["body"]["hash"], file_tell + len(node_chunk_body))
            node_chunk_body += b"\xDE\xAD\xBE\xEF\x08\0\0\0"

            self.set_pointer_target(node["body"]["hash"], file_tell + len(node_chunk_body), relative_to_hash_chunk=True)
            self.hash_chunk += struct.pack('<I', node["body"]["hash_flag"])
            self.hash_chunk += struct.pack('<I', node["body"]["hash_size"])

            hash = base64.b64decode(node["body"]["hash"])
            self.hash_chunk += hash + bytes(self.align(len(hash), 8) - len(hash))

        if _type == 'Frame':
            node_chunk_body += struct.pack('<f', node["body"]["minx"])
            node_chunk_body += struct.pack('<f', node["body"]["maxx"])
            node_chunk_body += struct.pack('<f', node["body"]["miny"])
            node_chunk_body += struct.pack('<f', node["body"]["maxy"])

        if _type == 'MetaScalar':
            node_chunk_body += struct.pack('<Q', node["body"]["unk"])

        file.write(node_chunk_body)

    def initialize_pointer_write_stuff(self):
        self.queued_pointer_writes = {}

    def set_pointer_source(self, object, location):
        entry = self.queued_pointer_writes.setdefault(id(object), {"_obj": object})
        entry["source_location"] = location

    def set_pointer_target(self, object, offset, relative_to_hash_chunk=False):
        entry = self.queued_pointer_writes.setdefault(id(object), {"_obj": object})
        entry["target_location"] = offset
        entry["relative_to_hash_chunk"] = relative_to_hash_chunk

    def do_pointer_writes(self, file):
        for key, value in self.queued_pointer_writes.items():
            try:
                file.seek(value["source_location"])
                target_location = value["target_location"]
                if value["relative_to_hash_chunk"]:
                    target_location += self.hash_chunk_pointer
                file.write(struct.pack("<Q", target_location))
            except KeyError as e:
                print(f"continuing pointer writes despite KeyError: {e}")
                if "source_location" in value:
                    print(f"(source_location: {hex(value['source_location'])})")
                if "target_location" in value:
                    print(f"(target_location: {hex(value['target_location'])})")
