#! /usr/bin/env python
import socketserver
from config import SERVER_IP, SERVER_PORT
from encrypt import encrypt, decrypt
from select import select
import logging
import socket
import struct

D = {'C': 0}


class LightHandler(socketserver.BaseRequestHandler):
    def handle_tcp(self, remote):
        sock = self.request
        sock_list = [sock, remote]
        while 1:
            read_list, _, _ = select(sock_list, [], [])
            if remote in read_list:
                data = remote.recv(8192)
                if not data:
                    break
                if (sock.send(encrypt(data)) <= 0):
                    logging.error('send to client error')
                    break

            if sock in read_list:
                data = sock.recv(8192)
                if not data:
                    break
                if (remote.send(decrypt(data)) <= 0):
                    logging.info('send to server error')
                    break

    def handle(self):
        data = self.request.recv(1)
        if not data:
            return
        D['C'] += 1
        logging.info('client connected [{}]'.format(D['C']))

        addr_bytes_length = data[0]
        addr = self.request.recv(addr_bytes_length)
        addr = decrypt(addr).decode()
        addr_port = struct.unpack("!H", self.request.recv(2))[0]
        logging.info("connecting to {}:{}".format(addr, addr_port))
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            remote.connect((addr, addr_port))
        except:
            logging.error('cannot connect to {}:{}'.format(addr, addr_port))
            return
        logging.info("waiting for {}:{}".format(addr, addr_port))
        try:
            self.handle_tcp(remote)
        finally:
            remote.close()
        D['C'] -= 1
        logging.info('client closed [{}]'.format(D['C']))


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s: %(message)s',
        level=logging.DEBUG,
    )
    server = ThreadedTCPServer((SERVER_IP, SERVER_PORT), LightHandler)
    logging.info('Proxy running at {}:{} ...'.format(
        SERVER_IP, SERVER_PORT))
    server.serve_forever()
