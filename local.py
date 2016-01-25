#! /usr/bin/env python3
from config import LOCAL_IP, LOCAL_PORT, SERVER_IP, SERVER_PORT
from select import select
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
                data = remote.recv(8192)
                if not data:
                    break
                if (sock.send(cipher.decrypt(data)) <= 0):
                    break
            if sock in read_list:
                data = sock.recv(8192)
                if not data:
                    break
                if (remote.send(cipher.encrypt(data)) <= 0):
                    break

    def handle(self):
            logging.info("got connection from {}".format(self.client_address[0]))

            data = self.request.recv(3)
            if len(data) != 3:
                logging.error("not socks5 or packet issue")
                return
            if not data or data[0] != 5:
                logging.error("not socks5")
                return

            # Send initial SOCKS5 response
            self.request.sendall(b'\x05\x00')
            data = self.request.recv(4)
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
