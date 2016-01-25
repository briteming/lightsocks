#! /usr/bin/env python3
from config import LOCAL_IP, LOCAL_PORT, SERVER_IP, SERVER_PORT
from select import select
from tools import safe_recv, u16_to_bytes, bytes_to_int
import socketserver
import logging
import socket
import struct
import cipher

D = {'R': 0}


class Socket5Handler(socketserver.BaseRequestHandler):
    def handle_tcp(self, remote):
        sock = self.request
        sock_list = [sock, remote]
        while True:
            read_list, _, _ = select(sock_list, [], [])
            if remote in read_list:
                data = safe_recv(remote, 2)
                if data is None:
                    break
                length = bytes_to_int(data)
                logging.debug('receiving data from remote: {}'.format(length))
                data = safe_recv(remote, length)
                if not data:
                    break
                dec = cipher.decrypt(data)
                if (sock.send(dec) <= 0):
                    break

            if sock in read_list:
                data = sock.recv(8192)
                if not data:
                    break
                enc = cipher.encrypt(data)
                length = len(enc)
                remote.send(u16_to_bytes(length))
                logging.debug('send data to server: {}'.format(length))
                if (remote.send(enc) <= 0):
                    break

    def handle(self):
        logging.info("got connection from {}".format(self.client_address[0]))
        data = safe_recv(self.request, 1)
        if data is None:
            return
        if data[0] != 5:
            logging.error("socks version not 5")
            return
        data = safe_recv(self.request, 1)
        if data is None:
            return
        length = bytes_to_int(data)
        data = safe_recv(self.request, length)
        if data is None:
            return
        logging.debug('got client initial data')

        # Send initial SOCKS5 response
        self.request.sendall(b'\x05\x00')
        logging.debug('replied \\x05\\x00 to client')

        data = safe_recv(self.request, 4)
        if data is None:
            logging.error('ver, cmd, rsv, atyp not received')
            return

        logging.debug('ver, cmd, rsv, atyp = {}'.format(data))
        if len(data) != 4:
            logging.error("packet loss")
            return

        ver, cmd, rsv, atyp = data
        if cmd != 1:
            logging.error('bad cmd value: {}'.format(cmd))
            return
        if atyp != 3:
            logging.error('bad atyp value: {}'.format(atyp))
            return

        addr_len = ord(self.request.recv(1))
        addr = self.request.recv(addr_len)
        addr_port = self.request.recv(2)
        logging.info('want to access {}:{}'.format(
            addr.decode(), int.from_bytes(addr_port, 'big')
        ))

        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            remote.connect((SERVER_IP, SERVER_PORT))
        except:
            logging.error('cannot connect to lightsocks server.')
            return
        D['R'] += 1
        logging.info('connected proxy server [{}]'.format(D['R']))

        # Reply to client to estanblish the socks v5 connection
        reply = b"\x05\x00\x00\x01"
        reply += socket.inet_aton('0.0.0.0')
        reply += struct.pack("!H", 0)
        self.request.sendall(reply)

        # encrypt address before sending it
        addr = cipher.encrypt(addr)
        dest_address = bytearray()
        dest_address += len(addr).to_bytes(1, 'big')
        dest_address += addr
        dest_address += addr_port
        remote.sendall(dest_address)
        try:
            self.handle_tcp(remote)
        finally:
            remote.close()
            D['R'] -= 1
            logging.info('disconnected from proxy server [{}]'.format(D['R']))


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
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
        format='[%(asctime)s][%(levelname)s] %(message)s',
        level=logging.INFO,
        filename=log_file,
    )
    server = ThreadedTCPServer((LOCAL_IP, local_port), Socket5Handler)
    logging.info('Local server running at {}:{} ...'.format(
        LOCAL_IP, local_port))
    server.serve_forever()
