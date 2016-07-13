# http://stackoverflow.com/a/12525165/665869
import base64
try:
    from Crypto.Cipher import AES
    from Crypto import Random
except:
    print('Cannot input Crypto, please install it:')
    print('sudo pip3 install pycrypto==2.6.1')
    exit(1)

from config import KEY


class AESCipher:
    def __init__(self, key):
        self.key = key

    def encrypt(self, raw):
        IV = Random.new().read(16)
        cipher = AES.new(self.key, AES.MODE_CFB, IV)
        return IV + cipher.encrypt(raw)

    def decrypt(self, enc):
        IV = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CFB, IV)
        return cipher.decrypt(enc[16:])


ci = AESCipher(KEY)


def decrypt(enc):
    return ci.decrypt(enc)


def encrypt(raw):
    return ci.encrypt(raw)


if __name__ == '__main__':
    raw = b'hello bob'
    enc = encrypt(raw)
    assert decrypt(enc) == raw

    raw = b'hello bob' * 1000
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
