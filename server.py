#! /usr/bin/env python
from config import SERVER_IP, SERVER_PORT
import SocketServer

class Socket5Handler(SocketServer.BaseRequestHandler):
    def handle(self):
        self.data = self.request.recv(1024).strip()
        print "{} wrote:".format(self.client_address[0])
        print self.data
        # just send back the same data, but upper-cased
        self.request.sendall(self.data.upper())

if __name__ == "__main__":
    server = SocketServer.TCPServer((SERVER_IP, SERVER_PORT), Socket5Handler)
    print 'Server running at %s ...' % SERVER_PORT
    server.serve_forever()
