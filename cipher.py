# http://stackoverflow.com/a/12525165/665869
import base64
from Crypto.Cipher import AES
from Crypto import Random
from config import KEY

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS).encode()
unpad = lambda s : s[:-ord(s[len(s)-1:])]


class AESCipher:
    def __init__(self, key):
        self.key = key

    def encrypt(self, raw):
        raw = pad(raw)
        iv = Random.new().read( AES.block_size )
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(enc[16:]))


ci = AESCipher(KEY)


def decrypt(enc):
    return ci.decrypt(enc)


def encrypt(raw):
    return ci.encrypt(raw)


if __name__ == '__main__':
    raw = b'hello bob'
    enc = encrypt(raw)
    assert decrypt(enc) == raw
    print("OK.")
    print("")
    s_32_1 = ''.join(['\\x{:02X}'.format(x) for x in Random.get_random_bytes(8)])
    print("KEY = b'{}' \\".format(s_32_1))
    s_32_2 = ''.join(['\\x{:02X}'.format(x) for x in Random.get_random_bytes(8)])
    print("    b'{}' \\".format(s_32_2))
    s_32_3 = ''.join(['\\x{:02X}'.format(x) for x in Random.get_random_bytes(8)])
    print("    b'{}' \\".format(s_32_3))
    s_32_4 = ''.join(['\\x{:02X}'.format(x) for x in Random.get_random_bytes(8)])
    print("    b'{}'".format(s_32_4))
