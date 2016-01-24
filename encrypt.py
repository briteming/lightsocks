from config import KEY
import hashlib
import struct


def get_table(key):
    if not isinstance(key, bytes):
        key = key.encode('utf-8')
    s = hashlib.md5(key).digest()
    a, b = struct.unpack('<QQ', s)
    table = list(range(256))
    for i in range(1, 1024):
        table.sort(key=lambda x: int(a % (x + i)))
    return ''.join([chr(x) for x in table])


PLAIN_TABLE = ''.join([chr(x) for x in range(256)])
ENCODE_TABLE = get_table(KEY)
DECODE_TABLE = str.maketrans(ENCODE_TABLE, PLAIN_TABLE)
ENCODE_TABLE = str.maketrans(PLAIN_TABLE, ENCODE_TABLE)


def encrypt(s):
    s = ''.join(chr(x) for x in s)
    return bytearray([ord(x) for x in s.translate(ENCODE_TABLE)])


def decrypt(s):
    s = ''.join(chr(x) for x in s)
    return bytearray([ord(x) for x in s.translate(DECODE_TABLE)])


if __name__ == "__main__":
    s = b'\x00\x04\x01\x05\xFF' * 2048
    e = encrypt(s)
    assert(len(e) == len(s))
    assert(e != s)
    assert(decrypt(e) == s)
    print("OK.")
