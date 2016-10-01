#! /usr/bin/env python
import cipher
import socketserver
import logging
import socket

from config import SERVER_IP, SERVER_PORT
from select import select
from tools import safe_recv, u16_to_bytes, bytes_to_int

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
                enc = cipher.encrypt(data)
                length = len(enc)
                logging.debug('send data to client: {}'.format(length))
                sock.send(u16_to_bytes(length))
                if (sock.send(enc) <= 0):
                    break
            if sock in read_list:
                data = safe_recv(sock, 2)
                if data is None:
                    break
                length = bytes_to_int(data)
                logging.debug('fetching data from client: {}'.format(length))

                data = safe_recv(sock, length)
                if data is None:
                    break
                dec = cipher.decrypt(data)
                logging.debug('send data to server: {}'.format(len(dec)))
                if (remote.send(dec) <= 0):
                    logging.debug('send to server error')
                    break

    def handle(self):
        try:
            data = self.request.recv(1)
        except ConnectionResetError:
            logging.error('ConnectionResetError')
            return
        except Exception as e:
            logging.error('Error: {}'.format(e))
            return
        if not data:
            return
        logging.info('client connected [{}]'.format(D['C']))

        addr_length = data[0]
        data_addr = safe_recv(self.request, addr_length)
        if data_addr is None:
            return

        try:
            addr = cipher.decrypt(data_addr).decode()
        except:
            logging.error('cannot decode: {}'.format(data_addr))
            return

        data_port = safe_recv(self.request, 2)
        if data_port is None:
            return
        port = bytes_to_int(data_port)
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
        except ConnectionResetError:
            logging.error('ConnectionResetError [{}]'.format(D['C']))
        except TimeoutError:
            logging.error('TimeoutError [{}]'.format(D['C']))
        except Exception as e:
            logging.exception('Error in handle_tcp(): {} [{}]'.format(e, D['C']))
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
