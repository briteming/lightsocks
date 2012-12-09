#! /usr/bin/env python
import logging
import socket
import struct
from select import select
from config import LOCAL_IP, LOCAL_PORT
import SocketServer

class Socket5Handler(SocketServer.BaseRequestHandler):
    def handle_tcp(self, sock, remote):
        sock_list = [sock, remote]
        try:
            while (1):
                read_list, _, _ = select(sock_list, [], [], 100)
                if remote in read_list:
                    data = remote.recv(8192)
                    if (sock.send(data) <= 0):
                        break
                if sock in read_list:
                    data = sock.recv(8192)
                    if len(data) == 0:
                        break;
                    if (remote.send(data) <= 0):
                        break
        finally:
            remote.close()
            sock.close()

    def handle(self):
        try:
            print "Connection from {}".format(self.client_address[0])
            data = self.request.recv(2)
            ver, nmethods = [ord(x) for x in data]
            if ver != 5:
                raise socket.error("Not socks V5")
            data = self.request.recv(nmethods)
            if not data:
                raise socks.error("Invalid Socket from %s" % self.client_address[0])
            self.request.sendall('\x05\x00')
            data = self.request.recv(4)
            ver, cmd, rsv, atyp = [ord(x) for x in data]
            if cmd != 1:
                raise socket.error("Bad cmd value")
            if atyp == 1:
                addr = self.request.recv(4)
            elif atyp == 3:
                addr_len = ord(self.request.recv(1))
                addr = self.request.recv(addr_len)
            else:
                raise socket.error("invalid atyp: %d", atyp)
            addr_port = struct.unpack("!H", self.request.recv(2))[0]

            # Reply to client to estanblish the socks v5 connection
            reply = "\x05\x00\x00\x01"
            reply += socket.inet_aton('0.0.0.0')
            reply += struct.pack("!H", 0)
            self.request.sendall(reply)

            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print "Fetch data from %s:%d ..." % (addr, addr_port),
            remote.connect((addr, addr_port))
            self.handle_tcp(self.request, remote)
            print "Done"
        except socket.error, e:
            logging.warn(e)
        finally:
            self.request.close()

if __name__ == "__main__":
    server = SocketServer.TCPServer((LOCAL_IP, LOCAL_PORT), Socket5Handler)
    print 'Server running at %s ...' % LOCAL_PORT
    server.serve_forever()
