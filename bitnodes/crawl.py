#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# crawl.py - Greenlets-based Bitcoin network crawler.
#
# Copyright (c) Addy Yeow Chin Heng <ayeowch@gmail.com>
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
Greenlets-based Bitcoin network crawler.
"""

from gevent import monkey
monkey.patch_all()

import gevent
import json
import logging
import os
#import requests
import socket
import sys
import time
from base64 import b32decode
from binascii import hexlify, unhexlify
#from collections import Counter
from ConfigParser import ConfigParser
#from ipaddress import ip_address, ip_network

from protocol import (
    ONION_PREFIX,
    TO_SERVICES,
    Connection,
    ConnectionError,
    ProtocolError,
)
from utils import get_keys, ip_to_network
from state import State

state = State()
CONF = {}

def extract_addrs(addr_msgs, now):
    """
    Adds all peering nodes with max. age of 24 hours into the crawl set.
    """
    num_peers = 0
    peers = []

    for addr_msg in addr_msgs:
        if 'addr_list' in addr_msg:
            for peer in addr_msg['addr_list']:
                age = now - peer['timestamp']  # seconds

                # Add peering node with age <= 24 hours into crawl set
                if age >= 0 and age <= CONF['max_age']:
                    address = peer['ipv4'] or peer['ipv6'] or peer['onion']
                    port = peer['port'] if peer['port'] > 0 else CONF['port']
                    services = peer['services']
                    if not address:
                        continue
                    #if is_excluded(address):
                    #    logging.debug("Exclude: %s", address)
                    #    continue
                    #redis_pipe.sadd('pending', (address, port, services))
                    num_peers += 1
                    peers.append((address,port,services))
    print(peers)
    return (num_peers, peers)


def connect(node):
    """
    Establishes connection with a node to:
    1) Send version message
    2) Receive version and verack message
    3) Send getaddr / getdata / getblock message
    4) Receive info from peer
    5) store acquired information in state
    """
    handshake_msgs = []
    addr_msgs = []
    data_msgs = []
    block_msgs = []
    
    (address, port, services) = node
    services = int(services)
    height = state.height

    if height:
        height = int(height)

    proxy = None
    if address.endswith(".onion"):
        proxy = CONF['tor_proxy']

    conn = Connection((address, int(port)),
                      (CONF['source_address'], 0),
                      magic_number=CONF['magic_number'],
                      socket_timeout=CONF['socket_timeout'],
                      proxy=proxy,
                      protocol_version=CONF['protocol_version'],
                      to_services=services,
                      from_services=CONF['services'],
                      user_agent=CONF['user_agent'],
                      height=height,
                      relay=CONF['relay'])
    try:
        logging.debug("Connecting to %s", conn.to_addr)
        conn.open()
        handshake_msgs = conn.handshake()
    except (ProtocolError, ConnectionError, socket.error) as err:
        logging.debug("%s: %s", conn.to_addr, err)

    
    if len(handshake_msgs) > 0:
        logging.debug("received handshake")
        version_msg = handshake_msgs[0]
        seen_height = version_msg.get('height', 0)
        logging.debug("received height: {}".format(seen_height))

        # Get latest block headers and send to 
        if seen_height > state.height:
            
            try:
                logging.debug("requesting headers from {}...".format(node))
                conn.getheaders(state.block_headers, last_block_hash=None, block=False)
            except (ProtocolError, ConnectionError, socket.error) as err:
                logging.debug("%s: %s", conn.to_addr, err)

            wait = 0
            while wait < CONF['socket_timeout']:
                wait += 1
                gevent.sleep(0.3)
                logging.debug("waiting for messages...")

                try:
                    msgs = conn.get_messages(commands=["headers"])
                except (ProtocolError, ConnectionError, socket.error) as err:
                    logging.debug("%s: %s", conn.to_addr, err)
                    break

                if msgs:
                    logging.debug("recieved headers: {}".format(msgs))
                    if header_lock.wait(3):
                        state.block_headers.update(msgs)
                        logging.debug("updated block headers successfully")
                    else:
                        logging.debug("failed to update block headers")
                    break


        # Otherwise get addrs
        
        else:
            try:
                conn.getaddr(block=False)
            except (ProtocolError, ConnectionError, socket.error) as err:
                logging.debug("%s: %s", conn.to_addr, err)

            addr_wait = 0
            while addr_wait < CONF['socket_timeout']:
                addr_wait += 1
                gevent.sleep(0.3)

                try:
                    msgs = conn.get_messages(commands=['addr'])
                except (ProtocolError, ConnectionError, socket.error) as err:
                    logging.debug("%s: %s", conn.to_addr, err)
                    break

                if msgs and any([msg['count'] > 1 for msg in msgs]):
                    addr_msgs = msgs
                    (num_peers, peers) = extract_addrs(addr_msg, now)
                    from_services = version_msg.get('services', 0)
                    if from_services != services:
                        logging.debug("%s Expected %d, got %d for services", conn.to_addr, services, from_services)
                        node = (address, port, from_services)
                    
                    if len(addr_msgs) > 1:
                        if state.addr_lock.wait(2):
                            state.addr_lock.acquire()
                            state.addrs.update(peers)
                            state.addrs.add(node) # re-add successful peer
                            state.addr_lock.release()
                            logging.debug("updated addrs successfully")
                        else:
                            logging.debug("failed to update addrs")
                    break

        # Process version msg
        #version_msg = handshake_msgs[0]
        #from_services = version_msg.get('services', 0)
        #if from_services != services:
        #    logging.debug("%s Expected %d, got %d for services", conn.to_addr,
        #                  services, from_services)
        #    node = (address, port, from_services)
        

        # Store height
        if seen_height > state.height:
            if state.height_lock.wait(3):
                state.height_lock.acquire()
                state.height = seen_height
                state.height_lock.release()
                logging.info("new height: {}".format(seen_height))
            else:
                logging.error("failed to update height: {}".format(seen_height))
    
        
    logging.debug("closing connection")
    conn.close()
    


def dump(timestamp, nodes):
    """
    Dumps data for reachable nodes into timestamp-prefixed JSON file and
    returns most common height from the nodes.
    """
    json_data = []

    for node in nodes:
        (address, port, services) = node[5:].split("-", 2)
        height_key = "height:{}-{}-{}".format(address, port, services)
        try:
            height = int(REDIS_CONN.get(height_key))
        except TypeError:
            logging.warning("%s missing", height_key)
            height = 0
        json_data.append([address, int(port), int(services), height])

    if len(json_data) == 0:
        logging.warning("len(json_data): %d", len(json_data))
        return 0

    json_output = os.path.join(CONF['crawl_dir'], "{}.json".format(timestamp))
    open(json_output, 'w').write(json.dumps(json_data))
    logging.info("Wrote %s", json_output)

    return Counter([node[-1] for node in json_data]).most_common(1)[0][0]



def task():
    """
    Assigned to a worker to retrieve (pop) a node from the crawl set and
    attempt to establish connection with a new node.
    """

    # select peer address
    if len(state.addrs):

        if state.addr_lock.wait(5):
            node = state.addrs.pop()

            # Skip IPv6 node
            if ":" in node[0] and not CONF['ipv6']:
                return

            connect(node)




def set_pending():
    """
    Initializes pending set in Redis with a list of reachable nodes from DNS
    seeders and hardcoded list of .onion nodes to bootstrap the crawler.
    """
    for seeder in CONF['seeders']:
        nodes = []

        try:
            ipv4_nodes = socket.getaddrinfo(seeder, None, socket.AF_INET)
        except socket.gaierror as err:
            logging.warning("%s", err)
        else:
            nodes.extend(ipv4_nodes)

        if CONF['ipv6']:
            try:
                ipv6_nodes = socket.getaddrinfo(seeder, None, socket.AF_INET6)
            except socket.gaierror as err:
                logging.warning("%s", err)
            else:
                nodes.extend(ipv6_nodes)

        for node in nodes:
            address = node[-1][0]
            if is_excluded(address):
                logging.debug("Exclude: %s", address)
                continue
            logging.debug("%s: %s", seeder, address)
            REDIS_CONN.sadd('pending', (address, CONF['port'], TO_SERVICES))

    if CONF['onion']:
        for address in CONF['onion_nodes']:
            REDIS_CONN.sadd('pending', (address, CONF['port'], TO_SERVICES))


def is_excluded(address):
    """
    Returns True if address is found in exclusion list, False if otherwise.
    """
    if address.endswith(".onion"):
        address = onion_to_ipv6(address)
    elif ip_address(unicode(address)).is_private:
        return True

    if ":" in address:
        address_family = socket.AF_INET6
        key = 'exclude_ipv6_networks'
    else:
        address_family = socket.AF_INET
        key = 'exclude_ipv4_networks'

    try:
        asn_record = ASN.asn(address)
    except AddressNotFoundError:
        asn = None
    else:
        asn = 'AS{}'.format(asn_record.autonomous_system_number)

    try:
        addr = int(hexlify(socket.inet_pton(address_family, address)), 16)
    except socket.error:
        logging.warning("Bad address: %s", address)
        return True

    if any([(addr & net[1] == net[0]) for net in CONF[key]]):
        return True

    if asn and asn in CONF['exclude_asns']:
        return True

    return False


def onion_to_ipv6(address):
    """
    Returns IPv6 equivalent of an .onion address.
    """
    ipv6_bytes = ONION_PREFIX + b32decode(address[:-6], True)
    return socket.inet_ntop(socket.AF_INET6, ipv6_bytes)


def list_excluded_networks(txt, networks=None):
    """
    Converts list of networks from configuration file into a list of tuples of
    network address and netmask to be excluded from the crawl.
    """
    if networks is None:
        networks = set()
    lines = txt.strip().split("\n")
    for line in lines:
        line = line.split('#')[0].strip()
        try:
            network = ip_network(unicode(line))
        except ValueError:
            continue
        else:
            networks.add((int(network.network_address), int(network.netmask)))
    return networks


def update_excluded_networks():
    """
    Adds bogons into the excluded IPv4 networks.
    """
    if not CONF['exclude_ipv4_bogons']:
        return
    url = "http://www.team-cymru.org/Services/Bogons/fullbogons-ipv4.txt"
    try:
        response = requests.get(url, timeout=15)
    except requests.exceptions.RequestException as err:
        logging.warning(err)
    else:
        if response.status_code == 200:
            CONF['exclude_ipv4_networks'] = list_excluded_networks(
                response.content,
                networks=CONF['initial_exclude_ipv4_networks'])
            logging.info("%d", len(CONF['exclude_ipv4_networks']))


def init_conf(argv):
    """
    Populates CONF with key-value pairs from configuration file.
    """
    conf = ConfigParser()
    conf.read(argv[1])
    CONF['logfile'] = conf.get('crawl', 'logfile')
    CONF['magic_number'] = unhexlify(conf.get('crawl', 'magic_number'))
    CONF['port'] = conf.getint('crawl', 'port')
    CONF['seeders'] = conf.get('crawl', 'seeders').strip().split("\n")
    CONF['workers'] = conf.getint('crawl', 'workers')
    CONF['debug'] = conf.getboolean('crawl', 'debug')
    CONF['source_address'] = conf.get('crawl', 'source_address')
    CONF['protocol_version'] = conf.getint('crawl', 'protocol_version')
    CONF['user_agent'] = conf.get('crawl', 'user_agent')
    CONF['services'] = conf.getint('crawl', 'services')
    CONF['relay'] = conf.getint('crawl', 'relay')
    CONF['socket_timeout'] = conf.getint('crawl', 'socket_timeout')
    CONF['cron_delay'] = conf.getint('crawl', 'cron_delay')
    CONF['snapshot_delay'] = conf.getint('crawl', 'snapshot_delay')
    CONF['max_age'] = conf.getint('crawl', 'max_age')
    CONF['ipv6'] = conf.getboolean('crawl', 'ipv6')
    CONF['ipv6_prefix'] = conf.getint('crawl', 'ipv6_prefix')
    CONF['nodes_per_ipv6_prefix'] = conf.getint('crawl',
                                                'nodes_per_ipv6_prefix')

    #CONF['exclude_asns'] = conf.get('crawl',
     #                               'exclude_asns').strip().split("\n")

    #CONF['exclude_ipv4_networks'] = list_excluded_networks(
      #  conf.get('crawl', 'exclude_ipv4_networks'))
    #CONF['exclude_ipv6_networks'] = list_excluded_networks(
     #   conf.get('crawl', 'exclude_ipv6_networks'))

    #CONF['exclude_ipv4_bogons'] = conf.getboolean('crawl',
     #                                             'exclude_ipv4_bogons')

    #CONF['initial_exclude_ipv4_networks'] = CONF['exclude_ipv4_networks']

    CONF['onion'] = conf.getboolean('crawl', 'onion')
    CONF['tor_proxy'] = None
    if CONF['onion']:
        tor_proxy = conf.get('crawl', 'tor_proxy').split(":")
        CONF['tor_proxy'] = (tor_proxy[0], int(tor_proxy[1]))
    CONF['onion_nodes'] = conf.get('crawl', 'onion_nodes').strip().split("\n")

    CONF['include_checked'] = conf.getboolean('crawl', 'include_checked')

    CONF['crawl_dir'] = conf.get('crawl', 'crawl_dir')
    if not os.path.exists(CONF['crawl_dir']):
        os.makedirs(CONF['crawl_dir'])
    state.height = int(conf.get('crawl', 'height'))
    



def main(argv):
    if len(argv) < 2 or not os.path.exists(argv[1]):
        print("Usage: crawl.py [config]")
        return 1

    # Initialize global conf
    init_conf(argv)
    state.addrs.add(("127.0.0.1", "18333", 1))

    # Initialize logger
    loglevel = logging.INFO
    if CONF['debug']:
        loglevel = logging.DEBUG

    logformat = ("[%(process)d] %(asctime)s,%(msecs)05.1f %(levelname)s "
                 "(%(funcName)s) %(message)s")
    logging.basicConfig(level=loglevel)#,
                        #format=logformat,
                        #filename=CONF['logfile'],
                        #filemode='a')
    print("Log: {}, press CTRL+C to terminate..".format(CONF['logfile']))

    #update_excluded_networks()
    # TODO (optional) set state to "running"

    # Spawn workers (greenlets) including one worker reserved for cron tasks
    workers = []
    
    #workers.append(gevent.spawn(cron))
    for _ in xrange(CONF['workers'] - len(workers)):
        workers.append(gevent.spawn(task))
    
    logging.info("Workers: %d", len(workers))
    result = gevent.joinall(workers)

    # TODO consolidate return values (?) and restart
    #state.height = max(heights)

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
