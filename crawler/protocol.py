#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# protocol.py - Bitcoin protocol access for bitnodes.
#
# Copyright (c) 2014 Addy Yeow Chin Heng <ayeowch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Bitcoin protocol access for bitnodes.
Reference: https://en.bitcoin.it/wiki/Protocol_specification

---------------------------------------------------------------------
               PACKET STRUCTURE FOR BITCOIN PROTOCOL
                     protocol version >= 70001
---------------------------------------------------------------------
[---MESSAGE---]
[ 4] MAGIC_NUMBER   (\xF9\xBE\xB4\xD9)                      uint32_t
[12] COMMAND                                                char[12]
[ 4] LENGTH         <I ( len(payload) )                     uint32_t
[ 4] CHECKSUM       ( sha256(sha256(payload))[:4] )         uint32_t
[..] PAYLOAD        see below

    [---VERSION_PAYLOAD---]
    [ 4] VERSION        <i                                  int32_t
    [ 8] SERVICES       <Q                                  uint64_t
    [ 8] TIMESTAMP      <q                                  int64_t
    [26] ADDR_RECV
        [ 8] SERVICES   <Q                                  uint64_t
        [16] IP_ADDR
            [12] IPV6   (\x00 * 10 + \xFF * 2)              char[12]
            [ 4] IPV4                                       char[4]
        [ 2] PORT       >H                                  uint16_t
    [26] ADDR_FROM
        [ 8] SERVICES   <Q                                  uint64_t
        [16] IP_ADDR
            [12] IPV6   (\x00 * 10 + \xFF * 2)              char[12]
            [ 4] IPV4                                       char[4]
        [ 2] PORT       >H                                  uint16_t
    [ 8] NONCE          <Q ( random.getrandbits(64) )       uint64_t
    [..] USER_AGENT     variable string
    [ 4] START_HEIGHT   <i                                  int32_t
    [ 1] RELAY          <? (since version >= 70001)         bool

    [---ADDR_PAYLOAD---]
    [..] COUNT          variable integer
    [..] ADDR_LIST      multiple of COUNT (max 1000)
        [ 4] TIMESTAMP  <I                                  uint32_t
        [ 8] SERVICES   <Q                                  uint64_t
        [16] IP_ADDR
            [12] IPV6   (\x00 * 10 + \xFF * 2)              char[12]
            [ 4] IPV4                                       char[4]
        [ 2] PORT       >H                                  uint16_t

    [---PING_PAYLOAD---]
    [ 8] NONCE          <Q ( random.getrandbits(64) )       uint64_t

    [---INV_PAYLOAD---]
    [..] COUNT          variable integer
    [..] INVENTORY      multiple of COUNT (max 50000)
        [ 4] TYPE       <I (0=error, 1=tx, 2=block)         uint32_t
        [32] HASH                                           char[32]
---------------------------------------------------------------------
"""

import binascii
import hashlib
import random
import socket
import struct
import sys
import time
from cStringIO import StringIO
from operator import itemgetter

MAGIC_NUMBER = "\xF9\xBE\xB4\xD9"
PROTOCOL_VERSION = 70001
SERVICES = 1
USER_AGENT = "/Satoshi:0.9.1/"
START_HEIGHT = 274475
RELAY = 0
DEFAULT_PORT = 8333
MAX_ADDR_COUNT = 1000

HEADER_LEN = 24


def sha256(data):
    return hashlib.sha256(data).digest()


class Serializer():
    def __init__(self):
        self.user_agent = USER_AGENT
        self.start_height = START_HEIGHT
        self.required_len = 0

    def serialize_msg(self, args):
        command = args[1]
        msg = [
            MAGIC_NUMBER,
            command + "\x00" * (12 - len(command)),
        ]

        payload = ""
        if command == "version":
            to_addr = args[0]
            from_addr = args[2]
            payload = self.serialize_version_payload(to_addr, from_addr)

        msg.extend([
            struct.pack("<I", len(payload)),
            sha256(sha256(payload))[:4],
            payload,
        ])

        msg = ''.join(msg)
        return msg

    def serialize_version_payload(self, to_addr, from_addr):
        payload = [
            struct.pack("<i", PROTOCOL_VERSION),
            struct.pack("<Q", SERVICES),
            struct.pack("<q", int(time.time())),
            self.serialize_network_address(to_addr),
            self.serialize_network_address(from_addr),
            struct.pack("<Q", random.getrandbits(64)),
            self.serialize_string(self.user_agent),
            struct.pack("<i", self.start_height),
            struct.pack("<?", RELAY),
        ]
        payload = ''.join(payload)
        return payload

    def deserialize_version_payload(self, data):
        msg = {}
        data = StringIO(data)

        msg['version'] = struct.unpack("<i", data.read(4))[0]
        msg['services'] = struct.unpack("<Q", data.read(8))[0]
        msg['timestamp'] = struct.unpack("<q", data.read(8))[0]
        msg['to_addr'] = self.deserialize_network_address(data)
        msg['from_addr'] = self.deserialize_network_address(data)
        msg['nonce'] = struct.unpack("<Q", data.read(8))[0]
        msg['user_agent'] = self.deserialize_string(data)
        msg['start_height'] = struct.unpack("<i", data.read(4))[0]

        try:
            msg['relay'] = struct.unpack("<?", data.read(1))[0]
        except struct.error:
            msg['relay'] = False

        return msg

    def deserialize_addr_payload(self, data):
        msg = {}
        data = StringIO(data)

        msg['count'] = self.deserialize_int(data)
        msg['addr_list'] = []
        for _ in xrange(msg['count']):
            try:
                network_address = self.deserialize_network_address(data, has_timestamp=True)
                msg['addr_list'].append(network_address)
            except:
                return msg['addr_list']

        return msg['addr_list']

    def serialize_network_address(self, addr):
        (ip_address, port) = addr
        network_address = [struct.pack("<Q", SERVICES)]
        if "." in ip_address:
            # unused (12 bytes) + ipv4 (4 bytes) = ipv4-mapped ipv6 address
            unused = "\x00" * 10 + "\xFF" * 2
            network_address.append(
                unused + socket.inet_pton(socket.AF_INET, ip_address))
        else:
            # ipv6 (16 bytes)
            network_address.append(
                socket.inet_pton(socket.AF_INET6, ip_address))
        network_address.append(struct.pack(">H", port))
        network_address = ''.join(network_address)
        return network_address

    def deserialize_network_address(self, data, has_timestamp=False):
        timestamp = None
        if has_timestamp:
            timestamp = struct.unpack("<I", data.read(4))[0]

        services = struct.unpack("<Q", data.read(8))[0]
        _ipv6 = data.read(12)
        _ipv4 = data.read(4)
        port = struct.unpack(">H", data.read(2))[0]

        ipv6 = socket.inet_ntop(socket.AF_INET6, _ipv6 + _ipv4)
        ipv4 = socket.inet_ntop(socket.AF_INET, _ipv4)

        if ipv4 in ipv6:
            ipv6 = ""  # use ipv4
        else:
            ipv4 = ""  # use ipv6

        return {
            'timestamp': timestamp,
            'services': services,
            'ipv6': ipv6,
            'ipv4': ipv4,
            'port': port,
        }

    def serialize_string(self, data):
        length = len(data)
        if length < 0xFD:
            return chr(length) + data
        elif length <= 0xFFFF:
            return chr(0xFD) + struct.pack("<H", length) + data
        elif length <= 0xFFFFFFFF:
            return chr(0xFE) + struct.pack("<I", length) + data
        return chr(0xFF) + struct.pack("<Q", length) + data

    def deserialize_string(self, data):
        length = self.deserialize_int(data)
        return data.read(length)

    def deserialize_int(self, data):
        length = struct.unpack("<B", data.read(1))[0]
        if length == 0xFD:
            length = struct.unpack("<H", data.read(2))[0]
        elif length == 0xFE:
            length = struct.unpack("<I", data.read(4))[0]
        elif length == 0xFF:
            length = struct.unpack("<Q", data.read(8))[0]
        return length

