import hashlib
from Crypto.Cipher import AES
from config import KEY

def md5(s):
    return hashlib.md5(s).hexdigest()

def get_key_iv(key):
    for i in range(4):
        key = md5(key + str(i))
    iv = md5(key)[:16]
    return key, iv

_KEY, _IV = get_key_iv(KEY)

def encrypt(text):
    aes = AES.new(_KEY, AES.MODE_CFB, _IV)
    return aes.encrypt(text)

def decrypt(ciphertext):
    aes = AES.new(_KEY, AES.MODE_CFB, _IV)
    return aes.decrypt(ciphertext)

if __name__ == "__main__":
    # simple test
    s = "Hello Bob. Please save me!"
    assert(encrypt(s) != s)
    assert(decrypt(encrypt(s)) == s)
    print "OK."
