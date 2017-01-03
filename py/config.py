import os.path

KEY = "x" * 16
SERVER_IP = "0.0.0.0"
SERVER_PORT = 1234
LOCAL_IP = "127.0.0.1"
LOCAL_PORT = 1080

if os.path.exists('./config_local.py'):
    from config_local import *
