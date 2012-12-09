import hashlib
from Crypto.Cipher import AES
KEY = '22'

def md5(s):
    return hashlib.md5(s).hexdigest()

def get_key_iv():
    for i in range(4):
        key = md5(key + str(i))
    iv = md5(key)[:16]
    return key, iv

key, iv = get_key_iv(KEY)

aes = AES.new(key, AES.MODE_CFB, iv)
plaintext = 'Hello Bob. Please save me!'
ciphertext = aes.encrypt(plaintext)
print ciphertext
aes = AES.new(key, AES.MODE_CFB, iv)
print aes.decrypt(ciphertext)
