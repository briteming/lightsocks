#! /usr/bin/env python
import socketserver
from config import SERVER_IP, SERVER_PORT
from encrypt import encrypt, decrypt
from select import select
import logging
import socket
import struct

D = {'C': 0}


def safe_recv(sock, size):
    data = sock.recv(size)
    if not data:
        return None

    size_left = size - len(data)
    while size_left > 0:
        time.sleep(0.01)
        _data = sock.recv(size_left)
        if not _data:
            return None
        data += _data
        size_left = size_left - len(_data)
    return data


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
        logging.info('client connected [{}]'.format(D['C']))

        addr_length = data[0]
        data_addr = safe_recv(self.request, addr_length)
        if data_addr is None:
            return

        addr = decrypt(data_addr).decode()
        data_port = safe_recv(self.request, 2)
        if data_port is None:
            return
        port = int.from_bytes(data_port, 'big')
        logging.info("connecting to {}:{}".format(addr, port))
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            remote.connect((addr, port))
        except:
            logging.error('cannot connect to {}:{}'.format(addr, port))
            return

        D['C'] += 1
        logging.info("waiting for {}:{}".format(addr, port))
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
        level=logging.INFO,
        filename='/tmp/lightsocks-server.log',
    )
    server = ThreadedTCPServer((SERVER_IP, SERVER_PORT), LightHandler)
    logging.info('Proxy running at {}:{} ...'.format(
        SERVER_IP, SERVER_PORT))
    server.serve_forever()
