# http://stackoverflow.com/a/12525165/665869
import hashlib
try:
    from Crypto.Cipher import AES
    from Crypto import Random
except:
    print('Cannot input Crypto, please install it:')
    print('sudo pip3 install pycrypto==2.6.1')
    exit(1)


from config import KEY

BLOCK_SIZE = 16


def pad(s):
    span = BLOCK_SIZE - (len(s) % BLOCK_SIZE)
    return s + bytes([span] * span)


def unpad(s):
    return s[0:-s[-1]]


class AESCipher:
    def __init__(self, key):
        if isinstance(key, str):
            key = key.encode()
        self.key = hashlib.sha256(key).digest()

    def encrypt(self, raw):
        IV = Random.new().read(16)
        cipher = AES.new(self.key, AES.MODE_CFB, IV, segment_size=128)
        encrypted = IV + cipher.encrypt(pad(raw))
        return encrypted

    def decrypt_old(self, enc):
        IV = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CFB, IV)
        return cipher.decrypt(enc[16:])

    def decrypt(self, encrypted):
        IV = encrypted[:16]
        cipher = AES.new(self.key, AES.MODE_CFB, IV, segment_size=128)
        data = cipher.decrypt(encrypted[16:])
        return unpad(data)


ci = AESCipher(KEY)


def decrypt(enc):
    return ci.decrypt(enc)


def encrypt(raw):
    return ci.encrypt(raw)


if __name__ == '__main__':
    raw = b'hello bob'
    enc = encrypt(raw)
    assert decrypt(enc) == raw

    raw = b'hello bob' * 10000
    enc = encrypt(raw)
    assert decrypt(enc) == raw
    print("OK.")
