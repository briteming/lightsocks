from config import KEY
import hashlib
import string
import struct

def get_table(key):
    """
    Algorithm from @clowwindy
    https://github.com/clowwindy/shadowsocks
    """
    s = hashlib.md5(key).digest()
    a, b = struct.unpack('<QQ', s)
    table = [ord(c) for c in string.maketrans('', '')]
    for i in xrange(1, 1024):
        table.sort(lambda x, y: int(a % (x + i) - a % (y + i)))
    return ''.join([chr(x) for x in table])

ENCODE_TABLE = get_table(KEY)
DECODE_TABLE = string.maketrans(ENCODE_TABLE, string.maketrans('', ''))

def encrypt(s):
    return s.translate(ENCODE_TABLE)

def decrypt(s):
    return s.translate(DECODE_TABLE)

if __name__ == "__main__":
    # simple test
    s = "Hello Bob. Please save me!"
    e = encrypt(s)
    assert(e != s)
    assert(decrypt(e) == s)
    print "OK."
