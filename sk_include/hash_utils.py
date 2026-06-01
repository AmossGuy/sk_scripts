#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Lookup3 hash implementation by Bob Jenkins, 1996.
# Adapted for Python with 32-bit constraints.

HASH_INITVAL = 123456789  # initval used by the ANB system

def _rot(x, k):
    return (((x) << (k)) | ((x) >> (32 - (k))))

def _mix(a, b, c):
    a &= 0xffffffff; b &= 0xffffffff; c &= 0xffffffff
    a -= c; a &= 0xffffffff; a ^= _rot(c, 4);  a &= 0xffffffff; c += b; c &= 0xffffffff
    b -= a; b &= 0xffffffff; b ^= _rot(a, 6);  b &= 0xffffffff; a += c; a &= 0xffffffff
    c -= b; c &= 0xffffffff; c ^= _rot(b, 8);  c &= 0xffffffff; b += a; b &= 0xffffffff
    a -= c; a &= 0xffffffff; a ^= _rot(c, 16); a &= 0xffffffff; c += b; c &= 0xffffffff
    b -= a; b &= 0xffffffff; b ^= _rot(a, 19); b &= 0xffffffff; a += c; a &= 0xffffffff
    c -= b; c &= 0xffffffff; c ^= _rot(b, 4);  c &= 0xffffffff; b += a; b &= 0xffffffff
    return a, b, c

def _final(a, b, c):
    a &= 0xffffffff; b &= 0xffffffff; c &= 0xffffffff
    c ^= b; c &= 0xffffffff; c -= _rot(b, 14); c &= 0xffffffff
    a ^= c; a &= 0xffffffff; a -= _rot(c, 11); a &= 0xffffffff
    b ^= a; b &= 0xffffffff; b -= _rot(a, 25); b &= 0xffffffff
    c ^= b; c &= 0xffffffff; c -= _rot(b, 16); c &= 0xffffffff
    a ^= c; a &= 0xffffffff; a -= _rot(c, 4);  a &= 0xffffffff
    b ^= a; b &= 0xffffffff; b -= _rot(a, 14); b &= 0xffffffff
    c ^= b; c &= 0xffffffff; c -= _rot(b, 24); c &= 0xffffffff
    return a, b, c

def hashlittle2(data, initval=0, initval2=0):
    length = lenpos = len(data)
    a = b = c = (0xdeadbeef + length + initval) & 0xffffffff
    c += initval2; c &= 0xffffffff

    p = 0
    while lenpos > 12:
        a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24)); a &= 0xffffffff
        b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); b &= 0xffffffff
        c += (ord(data[p+8]) + (ord(data[p+9])<<8) + (ord(data[p+10])<<16) + (ord(data[p+11])<<24)); c &= 0xffffffff
        a, b, c = _mix(a, b, c)
        p += 12
        lenpos -= 12

    if lenpos == 12: c += (ord(data[p+8]) + (ord(data[p+9])<<8) + (ord(data[p+10])<<16) + (ord(data[p+11])<<24)); b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24))
    if lenpos == 11: c += (ord(data[p+8]) + (ord(data[p+9])<<8) + (ord(data[p+10])<<16)); b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24))
    if lenpos == 10: c += (ord(data[p+8]) + (ord(data[p+9])<<8)); b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24))
    if lenpos == 9:  c += (ord(data[p+8])); b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24))
    if lenpos == 8:  b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24))
    if lenpos == 7:  b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24))
    if lenpos == 6:  b += ((ord(data[p+5])<<8) + ord(data[p+4])); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24))
    if lenpos == 5:  b += (ord(data[p+4])); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24))
    if lenpos == 4:  a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24))
    if lenpos == 3:  a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16))
    if lenpos == 2:  a += (ord(data[p+0]) + (ord(data[p+1])<<8))
    if lenpos == 1:  a += ord(data[p+0])
    a &= 0xffffffff; b &= 0xffffffff; c &= 0xffffffff
    if lenpos == 0: return c, b

    a, b, c = _final(a, b, c)
    return c, b

def hashlittle(data, initval=HASH_INITVAL):
    """Compute a lookup3 hashlittle hash of the given string."""
    c, b = hashlittle2(data, initval, 0)
    return c

def compute_hash(name: str) -> int:
    """Hash a plain-text name the same way the game does."""
    return hashlittle(name)

def load_wordlist(path: str) -> list[str]:
    """Load a wordlist file, returning stripped non-empty lines."""
    try:
        with open(path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def build_hash_map(wordlist: list[str]) -> dict[int, str]:
    """Pre-compute a {hash: word} lookup table from a wordlist."""
    return {hashlittle(word): word for word in wordlist}

def resolve_hash(hash_value: int, hash_map: dict[int, str]) -> str | None:
    """Return the plain-text name for a numeric hash, or None if unknown."""
    return hash_map.get(hash_value)
