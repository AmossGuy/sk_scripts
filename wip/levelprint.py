"""
Note: This script is a fork of aknetk's work. The original can be found here:

https://github.com/aknetk/ShovelKnightRE/blob/91b98d9ac3a0706f68eda3ef77202f6069e305cb/levelprint.py
"""

import sys
import struct
from collections import namedtuple
from time import sleep
from pathlib import Path
import os
import io
import zlib
import math
from PIL import Image
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.dom import minidom
from xml.etree import ElementTree

import hashlib

def _exit(msg):
    print(msg)
    print("Exiting in 1 second..")
    sleep(1)
    sys.exit(-1)

# https://docs.python.org/3/library/struct.html#format-characters

# meta.dat
# I: string count
# [
# H: string length
# str: filename
# ]

def prettifyXML(elem):
    rough_string = ElementTree.tostring(elem, "utf8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

class WFLZ:
    def decomp_bytearr(self, bytearr):
        return bytearr
    def comp_bytearr(self, bytearr):
        print()
        return bytearr
    def decomp_file(self, file):
        start_pos = file.tell()

        wfLZ_Header = struct.unpack("III", file.read(0xC))
        # wfLZ_HeaderChunked = struct.unpack("IIII", file.read(0x10))
        magic = wfLZ_Header[0]
        compressedSize = wfLZ_Header[1]
        decompressedSize = wfLZ_Header[2]

        firstBlock = struct.unpack("HBB", file.read(0x4))
        # dist = firstBlock[0]
        # length = firstBlock[1]
        numLiterals = firstBlock[2]

        dist = -1
        len = -1

        outarray = bytearray(decompressedSize)
        outindex = 0

        WFLZ_BLOCK_SIZE = 4
        WFLZ_MIN_MATCH_LEN = WFLZ_BLOCK_SIZE + 1
        WFLZ_MAX_MATCH_LEN = (0xFF - 1) + WFLZ_MIN_MATCH_LEN

        while 1:
            if numLiterals != 0:
                while numLiterals > 0:
                    outarray[outindex] = struct.unpack("B", file.read(0x1))[0]
                    outindex += 1
                    numLiterals -= 1
            elif dist == 0 and len == 0:
                return outarray

            block = struct.unpack("HBB", file.read(0x4))
            dist = block[0]
            len = block[1]
            numLiterals = block[2]

            if len != 0:
                cpySrc = outindex - dist;
                len += WFLZ_MIN_MATCH_LEN - 1;
                for i in range(len):
                    outarray[outindex] = outarray[cpySrc + i]
                    outindex += 1
        return outarray
    # Thanks Shane!
    def comp_file(self, file):
        return bytearray(0)

def ReadType(file, type):
    return struct.unpack(type, file.read({ "B": 1, "H": 2, "I": 4 }[type]))[0]
def ReadTypeBE(file, type):
    return struct.unpack(">" + type, file.read({ "B": 1, "H": 2, "I": 4 }[type]))[0]
def ReadRSDKString(file):
    return file.read(ReadType(file, "B")).decode("utf8").split('\0', 1)[0]
def ReadString(file):
    str = ""
    bb = ReadType(file, "B")
    while bb != 0:
        str += "%c" % bb
        bb = ReadType(file, "B")
    return str
def ReadCompressed(file, type):
    compressedSize = ReadType(file, "I") - 4
    decompressedSize = ReadTypeBE(file, "I")
    buff = file.read(compressedSize)
    buff = zlib.decompress(buff)

    typesize = { "B": 1, "H": 2, "I": 4 }[type]
    count = len(buff) / typesize

    return struct.unpack(str(count) + type, buff)

def WriteType(file, type, value):
    file.write(struct.pack(type, value))
def WriteTypeBE(file, type, value):
    file.write(struct.pack(">" + type, value))
def WriteRSDKString(file, value):
    WriteType(file, "B", len(value))
    file.write(bytearray(value, "utf8"))
def WriteCompressed(file, type, value):
    typesize = { "B": 1, "H": 2, "I": 4 }[type]

    count = len(value)
    decompressedSize = count * typesize
    buff = struct.pack(str(count) + type, *value)
    buff = zlib.compress(buff)

    compressedSize = len(buff)
    WriteType(file, "I", compressedSize + 4)
    WriteTypeBE(file, "I", decompressedSize)
    file.write(buff)

def ROL4(n, d):
    n &= 0xFFFFFFFF
    return ((n << d) | (n >> (32 - d))) & 0xFFFFFFFF
def ROR4(n, d):
    n &= 0xFFFFFFFF
    return ((n >> d) | (n << (32 - d)) & 0xFFFFFFFF) & 0xFFFFFFFF
# The cleaner source: http://www.burtleburtle.net/bob/hash/doobs.html
def YCG_Hash(string, length, initialHash):
    stringBytes = string.encode("utf8")
    stringBuff = io.BytesIO(stringBytes)

    index = 0
    hashA = (length + initialHash + 0xDEADBEEF) & 0xFFFFFFFF
    hashB = (length + initialHash + 0xDEADBEEF) & 0xFFFFFFFF
    hashC = (length + initialHash + 0xDEADBEEF) & 0xFFFFFFFF

    while length > 12:
        sHashA = hashA
        sHashB = hashB
        sHashC = hashC
        for i in range(min(length, 4)):
            sHashC += ReadType(stringBuff, "B") << ((i & 3) << 3)
            sHashC &= 0xFFFFFFFF
            length -= 1
        for i in range(min(length, 4)):
            sHashB += ReadType(stringBuff, "B") << ((i & 3) << 3)
            sHashB &= 0xFFFFFFFF
            length -= 1
        for i in range(min(length, 4)):
            sHashA += ReadType(stringBuff, "B") << ((i & 3) << 3)
            sHashA &= 0xFFFFFFFF
            length -= 1

        a = (sHashC - sHashA + 0x100000000) ^ ROL4(sHashA, 4)
        a1 = sHashB + sHashA
        b = (sHashB - a + 0x100000000) ^ ROL4(a, 6)
        b1 = a1 + a
        c = (a1 - b + 0x100000000) ^ ROL4(b, 8)
        c1 = b1 + b
        d = (b1 - c + 0x100000000) ^ ROL4(c, 16)
        d1 = c1 + c
        e = (c1 - d + 0x100000000) ^ ROR4(d, 13)
        hashC = d1 + d
        hashA = (d1 - e + 0x100000000) ^ ROL4(e, 4)
        hashB = hashC + e

    if length <= 12:
        for i in range(min(length, 4)):
            hashC += ReadType(stringBuff, "B") << ((i & 3) << 3)
            hashC &= 0xFFFFFFFF
            length -= 1
        for i in range(min(length, 4)):
            hashB += ReadType(stringBuff, "B") << ((i & 3) << 3)
            hashB &= 0xFFFFFFFF
            length -= 1
        for i in range(min(length, 4)):
            hashA += ReadType(stringBuff, "B") << ((i & 3) << 3)
            hashA &= 0xFFFFFFFF
            length -= 1

    # Finish
    a = (hashB ^ hashA) - ROL4(hashB, 14) + 0x100000000
    a &= 0xFFFFFFFF
    b = (hashC ^ a) - ROL4(a, 11) + 0x100000000
    b &= 0xFFFFFFFF
    c = (b ^ hashB) - ROR4(b, 7) + 0x100000000
    c &= 0xFFFFFFFF
    d = (c ^ a) - ROL4(c, 16) + 0x100000000
    d &= 0xFFFFFFFF
    e = (((b ^ d) - ROL4(d, 4) + 0x100000000) ^ c) - ROL4((b ^ d) - ROL4(d, 4) + 0x100000000, 14) + 0x100000000
    e &= 0xFFFFFFFF
    f = ((e ^ d) - ROR4(e, 8)) + 0x100000000
    f &= 0xFFFFFFFF
    return f

class LTBClass:
    def __init__(self, ltb_file):
        if ltb_file.suffix == '.ltb':
            self.unpack(ltb_file)
        else:
            _exit("Error: This is not a valid .LTB file!")

    def unpack(self, ltb_file):
        self.file = open(ltb_file, 'rb')

        file = self.file
        # path_hash = unpack(file, 4)

        # fpath = "levels/core/plainsOfPassage.ltb"
        # print("File Hash: 0x%08X" % YCG_Hash(fpath, len(fpath), 123456789))

        self.ltb_start = ltb_start = 0
        file.seek(ltb_start)

        layerFormatHeader = struct.unpack("IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII", file.read(0x90))

        unk_0x00 = layerFormatHeader[0]
        unk_0x04 = layerFormatHeader[1]
        tileSize = layerFormatHeader[2]
        chunkWidth = layerFormatHeader[3]
        chunkHeight = layerFormatHeader[4]
        layerInfoCount = layerFormatHeader[5]
        layerInfoOffset = layerFormatHeader[6]
        vertexBufferInfoCount = layerFormatHeader[9]
        vertexBufferInfoOffset = layerFormatHeader[10]
        textureFormatInfoCount = layerFormatHeader[13]
        textureFormatInfoOffset = layerFormatHeader[14]
        chunkCount = layerFormatHeader[17]
        chunkOffset = layerFormatHeader[18]
        tileBufferCount = layerFormatHeader[21]
        tileBufferOffset = layerFormatHeader[22]
        uvPointCount = layerFormatHeader[25]
        uvPointOffset = layerFormatHeader[26]
        staticVertexDataCount = layerFormatHeader[29]
        staticVertexDataOffset = layerFormatHeader[30]
        attachedFileCount = layerFormatHeader[33]
        attachedFileOffset = layerFormatHeader[34]

        print("LayerFormat Header:")
        print("-------------------")
        print("Tile Size: %d" % tileSize)
        print("Layer Info Count: %d" % layerInfoCount)
        print("Layer Info Offset: 0x%X" % layerInfoOffset)
        print("VertexBufferInfo Count: %d" % vertexBufferInfoCount)
        print("VertexBufferInfo Offset: 0x%X" % vertexBufferInfoOffset)
        print("Texture Info Count: %d" % textureFormatInfoCount)
        print("Texture Info Offset: 0x%X" % textureFormatInfoOffset)
        print("Chunk Tile Buffer Start Count: %d" % chunkCount)
        print("Chunk Tile Buffer Start Offset: 0x%X" % chunkOffset)
        print("Tile Buffer Count: %d" % tileBufferCount)
        print("Tile Buffer Offset: 0x%X" % tileBufferOffset)
        print("UV Count: %d" % uvPointCount)
        print("UV Offset: 0x%X" % uvPointOffset)
        print("Static Vertex Data Count: %d" % staticVertexDataCount)
        print("Static Vertex Data Offset: 0x%X" % staticVertexDataOffset)
        print("Attached File Offset Count: %d" % attachedFileCount)
        print("Attached File Offset List Offset: 0x%X" % attachedFileOffset)
        print("")

        # Layer Info List
        self.layerInfo = namedtuple("LayerInfo", "name nameHash unk1 unk2 cameraMultX unk3 cameraMultY unk4 unk5 unk6 unkI7 unkI8 unkI9 vertexBufferInfoIndex isUsingStaticVertexBuffer unkI10 chunkXCount chunkYCount chunkIDStart offsetX offsetY startX startY endX endY")
        self.layerInfoList = [None] * layerInfoCount

        file.seek(ltb_start + layerInfoOffset)
        for i in range(layerInfoCount):
            self.layerInfoList[i] = self.layerInfo._make(struct.unpack("32sIffffffffIIIIIIIIIffIIII", file.read(0x80)))

        # Vertex Buffer Info List
        self.vertexBufferInfo = namedtuple("VertexBufferInfo", "unk1 textureIndex vertexCount unk4 unk5")
        self.vertexBufferInfoList = [None] * vertexBufferInfoCount

        file.seek(ltb_start + vertexBufferInfoOffset)
        for i in range(vertexBufferInfoCount):
            self.vertexBufferInfoList[i] = self.vertexBufferInfo._make(struct.unpack("IIIII", file.read(0x14)))

        # Texture Format Info
        self.textureFormatInfo = namedtuple("TextureFormatInfo", "unk1 isCompressed width height unk2 unk3 unk4 unk5 unk6 unk7 unk8 unk9 unk10 unk11 unk12 unk13 unk14 unk15 size")
        self.textureFormatInfoList = [None] * textureFormatInfoCount

        file.seek(ltb_start + textureFormatInfoOffset)
        for i in range(textureFormatInfoCount):
            self.textureFormatInfoList[i] = self.textureFormatInfo._make(struct.unpack("IIIIfIiiiiiiiiiiiiI", file.read(0x4C)))

        # Chunk Infos
        self.chunkInfo = namedtuple("ChunkInfo", "tileBufferStart")
        self.chunkInfoList = [None] * chunkCount

        file.seek(ltb_start + chunkOffset)
        for i in range(chunkCount):
            self.chunkInfoList[i] = self.chunkInfo._make(struct.unpack("I", file.read(0x4)))

        # tileBuffer
        self.tileBufferList = [0] * tileBufferCount

        file.seek(ltb_start + tileBufferOffset)
        for i in range(tileBufferCount):
            self.tileBufferList[i] = struct.unpack("H", file.read(0x2))[0]

        # self.uvPointList
        self.uvPoint = namedtuple("UVPoint", "u1 v1 u2 v2")
        self.uvPointList = [None] * uvPointCount

        file.seek(ltb_start + uvPointOffset)
        for i in range(int(uvPointCount / 2)):
            self.uvPointList[i] = self.uvPoint._make(struct.unpack("ffff", file.read(0x10)))

        # Static Vertex Data List
        self.staticVertexData = namedtuple("StaticVertexData", "x y z u v")
        self.staticVertexDataList = [None] * staticVertexDataCount

        file.seek(ltb_start + staticVertexDataOffset)
        for i in range(staticVertexDataCount):
            self.staticVertexDataList[i] = self.staticVertexData._make(struct.unpack("fffff", file.read(0x14)))

        # Attached File Offset List
        self.attachedFileList = [0] * attachedFileCount

        file.seek(ltb_start + attachedFileOffset)
        for i in range(attachedFileCount):
            self.attachedFileList[i] = struct.unpack("Q", file.read(0x8))[0]

class LVBClass:
    def __init__(self, lvb_file):
        if lvb_file.suffix == '.lvb':
            self.unpack(lvb_file)
        else:
            _exit("Error: This is not a valid .LVB file!")

    def unpack(self, ltb_file):
        self.file = open(ltb_file, 'rb')

        file = self.file
        # path_hash = unpack(file, 4)

        self.lvb_start = lvb_start = 0
        file.seek(lvb_start)

        # header = struct.unpack("IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII", file.read(0x150))
        header = struct.unpack("IIQIIQIIQIIQIIQIIQIIQ", file.read(0x70))

        unk_Value_0x00 = header[0]
        objectPropertyCountListCount = header[1]
        objectPropertyCountListOffset = header[2]
        objectInfoCount = header[3]
        unk_Count_0x10 = header[4]
        objectInfoListOffset = header[5]
        unk_Value_0x20 = header[6]
        rectangleBatchCount = header[7]
        rectangleBatchOffset = header[8]
        unk_Value_0x30 = header[9]
        rectListCount = header[10]
        rectListOffset = header[11]
        unk_Value_0x40 = header[12]
        propertyValueSetListCount = header[13]
        propertyValueSetListOffset = header[14]
        unk_Value_0x50 = header[15]
        unk_Count_0x50 = header[16]
        unk_Offset_0x50 = header[17]
        unk_Value_0x60 = header[18]
        unk_Count_0x60 = header[19]
        unk_Offset_0x60 = header[20]

        print("LayerObject Header:")
        print("-------------------")
        print("unk_Value_0x00: %d" % unk_Value_0x00)
        print("objectPropertyCountListCount: 0x%X" % objectPropertyCountListCount)
        print("objectPropertyCountListOffset: 0x%X" % objectPropertyCountListOffset)
        print("")
        print("objectInfoCount: 0x%X" % objectInfoCount)
        print("unk_Count_0x10: 0x%X" % unk_Count_0x10)
        print("objectInfoListOffset: 0x%X" % objectInfoListOffset)
        print("")
        print("rectangleBatchCount: 0x%X" % rectangleBatchCount)
        print("rectangleBatchOffset: 0x%X" % rectangleBatchOffset)
        print("")
        print("rectListCount: 0x%X" % rectListCount)
        print("rectListOffset: 0x%X" % rectListOffset)
        print("")
        print("unk_Value_0x40: %d" % unk_Value_0x40)
        print("Property Value Count: 0x%X" % propertyValueSetListCount)
        print("Property Value List Offset: 0x%X" % propertyValueSetListOffset)
        print("")
        print("unk_Count_0x50: 0x%X" % unk_Count_0x50)
        print("unk_Offset_0x50: 0x%X" % unk_Offset_0x50)
        print("")
        print("String List Size: %d" % unk_Count_0x60)
        print("String List Offset: 0x%X" % unk_Offset_0x60)
        print("")

        ### Property Count Map
        # Input:    ObjectID
        # Output:   Property Count
        self.objectPropertyCountMap = { }
        file.seek(lvb_start + objectPropertyCountListOffset)
        for i in range(objectPropertyCountListCount):
            packed = struct.unpack("II", file.read(0x8))
            self.objectPropertyCountMap[packed[0]] = packed[1]

        ### Object Infos
        self.objectInfo = namedtuple("ObjectInfo", "unkHash layerNameHash x y scalex scaley isUnk6 objectID unk7 gID propertyCount propertyIndexStart unk11")
        self.objectInfoList = [ None ] * objectInfoCount

        file.seek(lvb_start + objectInfoListOffset)
        for i in range(len(self.objectInfoList)):
            self.objectInfoList[i] = self.objectInfo._make(struct.unpack("IIffffIHHIIII", file.read(0x30)))
            object = self.objectInfoList[i]
            # print("pos (%f %f) isUnk6 %X unk7 %X gID %X propertyCount %X propertyIndexStart %X unk11 %X" % (object.x, object.y, object.isUnk6, object.unk7, object.gID, object.propertyCount, object.propertyIndexStart, object.unk11))

        ### Rectangle Batches
        self.rectangleBatch = namedtuple("RectangleBatch", "hash flag flag2 count start")
        self.rectangleBatchList = [ None ] * rectangleBatchCount
        file.seek(lvb_start + rectangleBatchOffset)
        for i in range(rectangleBatchCount):
            self.rectangleBatchList[i] = self.rectangleBatch._make(struct.unpack("IIIII", file.read(0x14)))

        ### Rectangle Infos
        self.rectangleInfo = namedtuple("RectangleInfo", "x y width height isUnk id")
        self.rectangleInfoList = [ None ] * rectListCount
        file.seek(lvb_start + rectListOffset)
        for i in range(rectListCount):
            self.rectangleInfoList[i] = self.rectangleInfo._make(struct.unpack("IIIIIi", file.read(0x18)))

        ### Unique Property Value Sets
        self.propertyValueSet = namedtuple("UniquePropertyValueSet", "hash stringOffset")
        self.propertyValueSetList = [ None ] * propertyValueSetListCount
        file.seek(lvb_start + propertyValueSetListOffset)
        for i in range(propertyValueSetListCount):
            self.propertyValueSetList[i] = self.propertyValueSet._make(struct.unpack("II", file.read(0x8)))

        ### Paths
        print("Paths:")
        print("------")
        paths = [0] * unk_Count_0x50
        file.seek(lvb_start + unk_Offset_0x50)
        for i in range(len(paths)):
            paths[i] = struct.unpack("Q", file.read(0x8))[0]

        for i in range(len(paths) - 1):
            file.seek(lvb_start + paths[i])
            object = struct.unpack("I32sIfffIIIIIIIIIffffffffffffff", file.read(0x90))
            print("%s" % (object[1].decode("utf8").split("\0", 1)[0]))
            print("0x%08X %f %f %f" % (object[0x2], object[0x3], object[0x4], object[0x5]))
            print("0x%08X 0x%08X 0x%08X 0x%08X" % (object[0x6], object[0x7], object[0x8], object[0x9]))
            print("0x%08X 0x%08X 0x%08X 0x%08X" % (object[0xA], object[0xB], object[0xC], object[0xD]))
            print("0x%08X" % (object[0xE]))
            for v in range(4):
                print("%.2f %.2f %.2f" % (object[0xF + v * 3], object[0x10 + v * 3], object[0x11 + v * 3]))
            print("%.2f %.2f %.2f" % (object[0x1A], object[0x1B], object[0x1C]))
        #     # print("0x%08X %s 0x%08X %f" % (object[12], object[13].decode("utf8").split("\0", 1)[0], object[14], object[15]))
        #     # print("0x%08X 0x%08X 0x%08X 0x%08X" % (object[0x10], object[0x11], object[0x12], object[0x13]))
        #     # print("0x%08X 0x%08X 0x%08X 0x%08X" % (object[0x14], object[0x15], object[0x16], object[0x17]))
        #     # print("0x%08X 0x%08X 0x%08X 0x%08X" % (object[0x18], object[0x19], object[0x1A], object[0x1B]))
        #     # print("0x%08X" % (object[0x1C]))
            print("")
        # print("")

        ### Value strings
        self.valueStringListMap = { }
        file.seek(lvb_start + unk_Offset_0x60)
        start_pos = file.tell()
        while file.tell() < start_pos + unk_Count_0x60:
            pos = file.tell() - start_pos
            self.valueStringListMap[pos] = ReadString(file)

        return

def LTBandLVBtoTiled(ltb, lvb, map_name):
    # Player pos 90.4 -468.99

    from levelprint_data import objectNameDict, parameterList
    parameterMap = { }
    for i in range(len(parameterList)):
        stri = parameterList[i]
        hash = YCG_Hash(stri, len(stri), 123456789)
        parameterMap[hash] = stri

    # print("Unique Property Value Sets:")
    # print("---------------------------")
    # discovered = 0
    # discoveredMax = 0
    # for i in range(len(lvb.propertyValueSetList)):
    #     propertyValue = lvb.propertyValueSetList[i]
    #     if propertyValue.hash in parameterMap.keys():
    #         print("Property %d Hash: %s   Value: %s" % (i, parameterMap[propertyValue.hash], lvb.valueStringListMap[propertyValue.stringOffset]))
    #         discovered += 1
    #     else:
    #         print("Property %d Hash: 0x%08X   Value: %s" % (i, propertyValue.hash, lvb.valueStringListMap[propertyValue.stringOffset]))
    #     discoveredMax += 1
    # print("Discovered %d / %d" % (discovered, discoveredMax))
    # print("")

    paletteInfo = ltb.textureFormatInfoList[0]
    ltb.file.seek(ltb.ltb_start + ltb.attachedFileList[0])
    paletteBytes = ltb.file.read(paletteInfo.size)

    print("width %d height %d size %d" % (paletteInfo.width, paletteInfo.height, paletteInfo.size))

    if not os.path.exists("../Scenes"):
        os.makedirs("../Scenes")

    wflz = WFLZ()
    tileset_export_list = []
    for i in range(len(ltb.attachedFileList)):
        image_file_name = map_name + "_image_%d.png" % i
        image_path = "../Scenes/" + image_file_name
        ltb.file.seek(ltb.ltb_start + ltb.attachedFileList[i])

        info = ltb.textureFormatInfoList[i]
        if info.isCompressed != 0:
            tileset_export_list.append({"image_name": image_file_name, "columns": info.width // 18, "rows": info.height // 18})

            bytearr = wflz.decomp_file(ltb.file)

            if info.width * info.height * 4 == len(bytearr):
                image = Image.frombytes('RGBA', (info.width, info.height), bytes(bytearr), 'raw')
                image.save(image_path)
            else:
                bytearrRGBA = [0] * len(bytearr) * 4
                for c in range(len(bytearr)):
                    cp = int(bytearr[c] * 32 / 255) << 2
                    bytearrRGBA[c * 4 + 0] = paletteBytes[cp + 0]
                    bytearrRGBA[c * 4 + 1] = paletteBytes[cp + 1]
                    bytearrRGBA[c * 4 + 2] = paletteBytes[cp + 2]
                    bytearrRGBA[c * 4 + 3] = paletteBytes[cp + 3]
                image = Image.frombytes('RGBA', (info.width, info.height), bytes(bytearrRGBA), 'raw')
                image.save(image_path)
        else:
            bytearr = ltb.file.read(info.size)
            if info.width * info.height * 4 == len(bytearr):
                image = Image.frombytes('RGBA', (info.width, info.height), bytes(bytearr), 'raw')
                image.save(image_path)

    layer_id = 1
    object_id = 1

    xml_map = Element("map")
    xml_map.set("version", "1.2")
    xml_map.set("tiledversion", "1.3.3")
    xml_map.set("orientation", "orthogonal")
    xml_map.set("renderorder", "right-down")
    xml_map.set("width", "25")
    xml_map.set("height", "25")
    xml_map.set("tilewidth", "16")
    xml_map.set("tileheight", "16")
    xml_map.set("infinite", "1")
    # xml_map.set("nextlayerid", "3")
    # xml_map.set("nextobjectid", "2")

    comment = Comment("Generated using ShovelKnightRE: https://github.com/aknetk/ShovelKnightRE")
    xml_map.append(comment)

    firstgid = 1
    for tileset in tileset_export_list:
        xml_tileset = SubElement(xml_map, "tileset")
        xml_tileset.set("firstgid", str(firstgid))
        xml_tileset.set("name", Path(tileset["image_name"]).stem)
        xml_tileset.set("tilewidth", "16")
        xml_tileset.set("tileheight", "16")
        xml_tileset.set("spacing", "2")
        xml_tileset.set("margin", "1")
        xml_tileset.set("tilecount", str(tileset["columns"] * tileset["rows"]))
        xml_tileset.set("columns", str(tileset["columns"]))
        SubElement(xml_tileset, "image", source=tileset["image_name"])
        firstgid += tileset["columns"] * tileset["rows"]

    tilebuffer = [[0] * 64 for i in range(64)]

    columncount = 28
    for i in range(len(ltb.staticVertexDataList) >> 2):
        # Z formation
        v1 = ltb.staticVertexDataList[i * 4 + 0]
        v2 = ltb.staticVertexDataList[i * 4 + 1]
        v3 = ltb.staticVertexDataList[i * 4 + 2]
        v4 = ltb.staticVertexDataList[i * 4 + 3]

        # Compare UVs to determine orientation
        flip_x = v1[3] > v2[3]
        flip_y = v1[4] > v2[4]

        mean_x = (v1[0] + v2[0] + v3[0] + v4[0]) / 4
        mean_y = (v1[1] + v2[1] + v3[1] + v4[1]) / 4

        x = mean_x / 0.1 + 240.0 # / 0.1, as this is undoes what game does internally
        y = mean_y / 0.1 + 160.0 # / 0.1, as this is undoes what game does internally
        z = v1[2]
        u = v1[3] * 512.0
        v = v1[4] * 512.0

        tile_x = math.floor(x / 16.0)
        tile_y = math.floor(y / 16.0)
        cell_x = math.floor(u / 18.0)
        cell_y = math.floor(v / 18.0)
        tilebuffer[tile_x][tile_y] = math.floor(cell_x + cell_y * columncount) + 1

    layerList_string = ""
    for i in range(len(ltb.layerInfoList)):
        layer = ltb.layerInfoList[i]
        visible = 1
        if layer.endX - layer.startX < -1:
            continue
        if layer.endY - layer.startY < -1:
            continue

        xml_layer = SubElement(xml_map, "layer")
        xml_layer.set("id", str(layer_id))
        xml_layer.set("name", layer.name.decode("utf8").split('\0', 1)[0])
        xml_layer.set("width", str(layer.endX - layer.startX + 1))
        xml_layer.set("height", str(layer.endY - layer.startY + 1))
        xml_layer.set("offsetx", str(layer.startX * 16))
        xml_layer.set("offsety", str(layer.startY * 16))
        xml_layer.set("visible", str(visible))
        layer_id += 1

        xml_data = SubElement(xml_layer, "data")
        xml_data.set("encoding", "csv")

        xml_properties = SubElement(xml_layer, "properties")
        xml_property = SubElement(xml_properties, "property")
        xml_property.set("name", "SCROLL_X_MULT")
        xml_property.set("type", "float")
        xml_property.set("value", "%f" % layer.cameraMultX)
        xml_property = SubElement(xml_properties, "property")
        xml_property.set("name", "SCROLL_Y_MULT")
        xml_property.set("type", "float")
        xml_property.set("value", "%f" % layer.cameraMultY)

        if layer.isUsingStaticVertexBuffer != 0:
            csv = ""
            first = True
            for ty in range(layer.endY - layer.startY + 1):
                for tx in range(layer.endX - layer.startX + 1):
                    if first:
                        csv += "%d" % (int(tilebuffer[tx][layer.endY - ty]))
                        first = False
                    else:
                        csv += ",%d" % (int(tilebuffer[tx][layer.endY - ty]))
            xml_layer.set("offsetx", "0.0")
            xml_layer.set("offsety", "0.0")
            xml_data.text = csv
        else:
            chunk_text = ""
            chunkStart = layer.chunkIDStart
            print(layer)
            for cy in range(layer.chunkYCount):
                for cx in range(layer.chunkXCount):
                    chunkID = chunkStart + cx + cy * layer.chunkXCount
                    tileStart = ltb.chunkInfoList[chunkID].tileBufferStart
                    if tileStart > 0:
                        csv = ""
                        first = True
                        for ty in range(16):
                            for tx in range(16):
                                tiledata = ltb.tileBufferList[tileStart + tx + ty * 16]
                                isSolid = tiledata & 0x8000
                                flip_x = tiledata & 0x2000
                                flip_y = tiledata & 0x4000
                                tile_id = tiledata & 0xFFF
                                tiled_out = tile_id

                                if tiledata & 0x1000:
                                    tiled_out += tileset_export_list[0]["columns"] * tileset_export_list[0]["rows"]

                                if tiled_out != 0:
                                    if flip_x != 0:
                                        tiled_out |= 0x80000000
                                    if flip_y != 0:
                                        tiled_out |= 0x40000000
                                if first:
                                    csv += "%d" % (int(tiled_out))
                                    first = False
                                else:
                                    csv += ",%d" % (int(tiled_out))

                        xml_chunk = SubElement(xml_data, "chunk")
                        xml_chunk.set("x", str(cx * 16))
                        xml_chunk.set("y", str(cy * 16))
                        xml_chunk.set("width", "16")
                        xml_chunk.set("height", "16")
                        xml_chunk.text = csv

    for b in range(len(lvb.rectangleBatchList)):
        batch = lvb.rectangleBatchList[b]
        xml_objectgroup = SubElement(xml_map, "objectgroup")
        xml_objectgroup.set("id", str(layer_id))
        xml_objectgroup.set("visible", "false")
        if batch.hash in parameterMap.keys():
            print(parameterMap[batch.hash])
            xml_objectgroup.set("name", parameterMap[batch.hash])
        else:
            xml_objectgroup.set("name", "Rect Layer %08X" % batch.hash)
        layer_id += 1
        for r in range(batch.start, batch.start + batch.count):
            recta = lvb.rectangleInfoList[r]
            xml_object = SubElement(xml_objectgroup, "object")
            xml_object.set("x", str(recta.x))
            xml_object.set("y", str(recta.y))
            xml_object.set("width", str(recta.width))
            xml_object.set("height", str(recta.height))
            xml_object.set("id", str(recta.id))
            object_id = recta.id + 1

    # parameterMap
    xml_objectgroup = SubElement(xml_map, "objectgroup")
    xml_objectgroup.set("id", str(layer_id))
    xml_objectgroup.set("name", "Object Layer %08X" % 0xDEADBEEF)
    layer_id += 1

    unk7s = {}
    # self.objectInfo = namedtuple("ObjectInfo", "unkHash layerNameHash x y scalex scaley unk6 objectID unk7 gID propertyCount propertyIndexStart unk11")

    for i in range(len(lvb.objectInfoList)):
        object = lvb.objectInfoList[i]
        oID = object.objectID & 0xFFF

        xml_object = SubElement(xml_objectgroup, "object")
        xml_object.set("x", str(object.x))
        xml_object.set("y", str(object.y))
        if oID in objectNameDict.keys():
            xml_object.set("name", objectNameDict[oID])
        else:
            xml_object.set("name", "UnknownObject %d" % oID)
        xml_object.set("id", str(object.gID & 0xFFFF))
        xml_point = SubElement(xml_object, "point")
        object_id += 1

        unk7s[object.unk7] = object.unk7

        xml_properties = SubElement(xml_object, "properties")

        p_count = lvb.objectPropertyCountMap[oID]
        p_start = object.propertyIndexStart
        p_end = p_start + object.propertyCount
        for p in range(p_start, p_end):
            valueSet = lvb.propertyValueSetList[p]
            property_name = "0x%08X" % valueSet.hash
            property_value = ""
            if valueSet.hash in parameterMap.keys():
                property_name = parameterMap[valueSet.hash]
            if valueSet.stringOffset in lvb.valueStringListMap.keys():
                property_value = lvb.valueStringListMap[valueSet.stringOffset]

            xml_property = SubElement(xml_properties, "property")
            xml_property.set("name", property_name)
            xml_property.set("type", "string")
            xml_property.set("value", property_value)

    print("unk7s")
    for u in unk7s.keys():
        print("u: %d" % u)

    open("../Scenes/" + map_name + ".tmx", "w").write(prettifyXML(xml_map))

    print("")

if __name__ == '__main__':
    # Verify the file exist and an arg was giving
    if not len(sys.argv) >= 2:
        _exit("Error: Please specify a target .ltb file.")
    if not Path(sys.argv[1]).is_file() and not Path(sys.argv[1]).is_dir():
        _exit("Error: The file '%s' was not found." % (sys.argv[1]))
    if not len(sys.argv) >= 3:
        _exit("Error: Please specify a target .lvb file.")
    if not Path(sys.argv[2]).is_file() and not Path(sys.argv[2]).is_dir():
        _exit("Error: The file '%s' was not found." % (sys.argv[2]))

    # Run it
    # os.chdir(Path(sys.argv[1]).parent)
    ltb = LTBClass(Path(sys.argv[1]))
    lvb = LVBClass(Path(sys.argv[2]))
    LTBandLVBtoTiled(ltb, lvb, Path(sys.argv[1]).stem)
    # LTBandLVBtoRSDKScene(ltb, lvb, "Plains")

_exit("Log: Program finished.")
