#! /usr/bin/env python

from config import LOCAL_IP, LOCAL_PORT, SERVER_IP, SERVER_PORT
from encrypt import encrypt, decrypt
from select import select
import SocketServer
import logging
import socket
import struct

class Socket5Handler(SocketServer.BaseRequestHandler):
    def handle_tcp(self, remote):
        sock = self.request
        sock_list = [sock, remote]
        try:
            while (1):
                read_list, _, _ = select(sock_list, [], [])
                if remote in read_list:
                    data = remote.recv(8192)
                    if (sock.send(decrypt(data)) <= 0):
                        break
                if sock in read_list:
                    data = sock.recv(8192)
                    if (remote.send(encrypt(data)) <= 0):
                        break
        finally:
            remote.close()
            sock.close()

    def handle(self):
        try:
            logging.info("Connection from {}".format(self.client_address[0]))
            # Here we do not need to recv exact bytes,
            # since we do not require clients to use any auth method
            data = self.request.recv(256)
            if not data or ord(data[0]) != 5:
                raise socket.error("Not socks5")
            # Send initial SOCKS5 response
            self.request.sendall('\x05\x00')
            data = self.request.recv(4)
            ver, cmd, rsv, atyp = [ord(x) for x in data]
            if cmd != 1:
                raise socket.error("Bad cmd value: %d" % cmd)
            if atyp != 3:
                raise socket.error("Bad atyp value: %d" % atyp)
            addr_len = ord(self.request.recv(1))
            addr = self.request.recv(addr_len)
            addr_port = self.request.recv(2)

            # Reply to client to estanblish the socks v5 connection
            reply = "\x05\x00\x00\x01"
            reply += socket.inet_aton('0.0.0.0')
            reply += struct.pack("!H", 0)
            self.request.sendall(reply)

            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.connect((SERVER_IP, SERVER_PORT))
            logging.info("Connect to %s" % addr)
            # encrypt address before sending it
            addr = encrypt(addr)
            dest_address = "%s%s%s" % (chr(len(addr)), addr, addr_port)
            remote.sendall(dest_address)
            self.handle_tcp(remote)
        except socket.error as e:
            logging.warn(e)
        finally:
            self.request.close()

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Lightsocks')
    parser.add_argument('--log-file', '-l', type=str)
    parser.add_argument('--port', '-p', type=int)
    args = parser.parse_args()

    local_port = args.port if args.port else LOCAL_PORT
    log_file = args.log_file if args.log_file else '/tmp/lightsocks.log'

    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s: %(message)s',
        level=logging.INFO,
        filename=log_file,
    )
    server = ThreadedTCPServer((LOCAL_IP, local_port), Socket5Handler)
    logging.info('Local server running at {}:{} ...'.format(
        LOCAL_IP, local_port))
    server.serve_forever()
