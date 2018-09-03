# -*- coding: utf-8 -*-
#client protocol. Returns deferred.
from twisted.internet import reactor, defer
from twisted.internet.protocol import Protocol
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint
from protocol import Serializer
import struct
import sys
import time
from twisted.internet.error import ConnectError
MAGIC_NUMBER = "\xF9\xBE\xB4\xD9"

sendMsg = '\xf9\xbe\xb4\xd9verack\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00]\xf6\xe0\xe2\xf9\xbe\xb4\xd9getaddr\x00\x00\x00\x00\x00\x00\x00\x00\x00]\xf6\xe0\xe2'

class BitcoinProtocol(Protocol):

    def __init__(self):
        self.flag = False
        self.packetlog = []
        self.results = {}
        self.results['time'] = time.time()

    def sendMessage(self, msg):
        self.transport.write(msg)

    def process_header(self, hdr):
        if hdr[:4] == MAGIC_NUMBER:
            self.command = hdr[4:16].strip("\x00")
            self.length = struct.unpack("<I", hdr[16:20])[0]
            self.checksum = hdr[20:24]
            return True
        return False

    def returnLog(self):
        d = defer.Deferred()
        def fire():
            if self.results.has_key('version'):

                self.results['addrs'] = []
                data = ''.join(self.packetlog)
                parts = data.split("\xf9\xbe\xb4\xd9addr\x00\x00\x00\x00\x00\x00\x00\x00")

                if len(parts) > 1:
                    for batch in parts[1:]:
                        try:
                            l = self.factory.ser.deserialize_addr_payload(batch[8:])
                            self.results['addrs'].extend(l)
                        except struct.error:
                            d.callback(None)

                d.callback(self.results)
            else:
                d.callback(None)


        reactor.callLater((self.factory.timeout-3), fire)
        reactor.callLater(self.factory.timeout, self.transport.loseConnection)
        return d

    def dataReceived(self, data):
        # if logging messages
        if self.flag:
            self.packetlog.append(data)

        # if expecting version message
        else:
            data_length = len(data)

            if data_length >= 24:
                is_new_packet = self.process_header(data[:24])

                if is_new_packet:
                    if self.command == "version":
                        self.flag = True
                        try:
                            self.results['version'] = self.factory.ser.deserialize_version_payload(data[24:])
                        except struct.error:
                            self.results['version'] = {}
                        #log.msg("sending verack and getAddr")
                        self.sendMessage(sendMsg)


    def connectionFailed(self, reason):
        pass
        #log.msg("connection failed, reason: ", reason.getErrorMessage())
    def connectionLost(self, reason):
        pass
        #log.msg("connection lost, reason: ", reason.getErrorMessage())

class GetterFactory(Factory):
    def __init__(self, addr, port, to):
        self.to_addr = addr
        self.to_port = port
        self.timeout = to

    def buildProtocol(self, addr):
        a = BitcoinProtocol()
        self.ser = Serializer()
        a.factory = self
        return a

def gotProtocol(p):
    if p:
        myaddr = p.transport.getHost()

        args = [(p.factory.to_addr, p.factory.to_port), "version", (myaddr.host, myaddr.port)]
        reactor.callLater(p.factory.timeout, p.transport.loseConnection)
        try:
            versionMsg = p.factory.ser.serialize_msg(args)
        except struct.error:
            raise ConnectError

        p.sendMessage(versionMsg)
        d = p.returnLog()
        return d

def protocolFail(res):
    return None

def get_endpoint(addr, port, timeout):
    endpoint = TCP4ClientEndpoint(reactor, addr, port)
    d = endpoint.connect(GetterFactory(addr,port,timeout))
    d.addCallback(gotProtocol)
    d.addErrback(protocolFail)
    return d
