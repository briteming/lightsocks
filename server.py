#! /usr/bin/env python
import SocketServer
from config import SERVER_IP, SERVER_PORT
from encrypt import encrypt, decrypt
from select import select
import logging
import socket
import struct

class LightHandler(SocketServer.BaseRequestHandler):
    def handle_tcp(self, remote):
        sock = self.request
        sock_list = [sock, remote]
        try:
            while (1):
                read_list, _, _ = select(sock_list, [], [])
                if remote in read_list:
                    data = remote.recv(8192)
                    if (sock.send(encrypt(data)) <= 0):
                        break
                if sock in read_list:
                    data = sock.recv(8192)
                    if (remote.send(decrypt(data)) <= 0):
                        break
        finally:
            remote.close()
            sock.close()

    def handle(self):
        try:
            data = self.request.recv(1)
            addr = self.request.recv(ord(data[0]))
            addr = decrypt(addr)
            addr_port = struct.unpack("!H", self.request.recv(2))[0]

            logging.info("Connecting to %s:%s" % (addr, addr_port))
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.connect((addr, addr_port))
            self.handle_tcp(remote)
        except socket.error, e:
            logging.warn(e)
        finally:
            self.request.close()

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)
    server = ThreadedTCPServer((SERVER_IP, SERVER_PORT), LightHandler)
    logging.info('Server running at %s ...' % SERVER_PORT)
    server.serve_forever()
