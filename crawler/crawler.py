#!/usr/bin/env python
# -*- coding: utf-8 -*-
from twisted.internet import reactor, defer
from client import get_endpoint
from twisted.python.logfile import DailyLogFile
import time
from pickle import dump
from twisted.python.util import untilConcludes
from twisted.internet.error import ConnectionRefusedError,ConnectError,TimeoutError
from subprocess import check_call
import pickle
import gzip
import random

lf = DailyLogFile("overlay.log", "/home/ubuntu/final/crawler/logs")

plist = []
addrlist = set()
faillist = set()
peerAddrList = set()
starttime = time.time()

### Labels ###
# 0 - live
# 1 - inferred live
# 2 - seen dead
#

def log(t, label, event):
    untilConcludes(lf.write, "%d:%d:%r\n" % (t,label, event))
    untilConcludes(lf.flush)


def wgetDone(failed):
    if not failed:
        global peerAddrList
        with gzip.open("pulls/addrs.gz", 'rb') as f:
            peerAddrList.update(pickle.load(f))
            print "peerAddrList is now ", peerAddrList

def gossip():
    d = defer.Deferred()
    d.addCallback(wgetDone)
    def fire():
        url = random.choice(plist) + "/addrs.gz"
        failed = 1
        try:
            failed = check_call(["wget","-q","-O", "pulls/addrs.gz",url])
        except:
            pass

        d.callback(failed)
    reactor.callLater(0,fire)
    return d

def gotResults(res):
    if not res:
        return (0, None)
    seenAddrs = []

    ts = res['time']
    f_addr = ''
    f_port = ''

    if res.has_key('version'):
        v = res['version']
        f_addr = v['from_addr']['ipv4']
        f_port = v['from_addr']['port']
        seenAddrs.append((f_addr,f_port))
        tolog = {}
        tolog['addr'] = f_addr
        tolog['port'] = f_port
        tolog['is_r'] = v['relay']
        tolog['vers'] = v['version']
        tolog['us_a'] = v['user_agent']
        tolog['time'] = v['timestamp']

        log(ts,0,tolog)

    if res.has_key('addrs'):
        inferred = []
        for a in res['addrs']:
            i_addr = a['ipv4']
            if i_addr:
                i_port = a['port']
                inferred.append((i_addr, i_port))

                tolog['addr'] = i_addr
                tolog['port'] = i_port
                tolog['i_ip'] = f_addr
                tolog['i_po'] = f_port
                tolog['time'] = a['timestamp']
                log(ts,1, tolog)

        seenAddrs.extend(inferred)
    return (1, seenAddrs)

def allDone(res):
    print "allDone!"
    # gets list results from each client

    newAddrs = set()
    badAddrs = set()

    global addrlist
    global faillist

    for tup in res:
        if tup[1][0]:
            newAddrs.update(tup[1][1])
        else:
            dead = tup[1][1]
            if dead:
                aproxfailtime = starttime + (starttime - time.time())/2.0
                badAddrs.add((dead['ip'],dead['po']))
                log(aproxfailtime, 2, dead)

    #remove unreachable and gossipped nodes
    toremove = faillist.intersection(badAddrs)
    addrlist.difference_update(toremove)
    addrlist.difference_update(peerAddrList)
    #write addrList for gossip
    with gzip.open("tmp/addrs.gz", 'wb') as f:
        pickle.dump(list(addrlist),f)
    #add newly seen addrs and update faillist
    addrlist.update(newAddrs)
    faillist = badAddrs
    lf.rotate()

    #runClients()
    reactor.stop()

def gotFail(failure, ad, po):
    failure.trap(ConnectionRefusedError, ConnectError, TimeoutError)
    print "caught failure: ", failure
    return (0,{'ip':ad, 'po':po})

def load_addr_seeds():
    global addrlist
    with open("config/seeds.pkl", 'rb') as sf:
        addrlist.update(pickle.load(sf))
        print "addrs loaded: ", addrlist

def runClients():
    with open("config/run",'r') as rf:
        r = rf.read().strip()
        print "run is ", r

    if r == '1':
        gossip()
        global starttime
        starttime = time.time()

        if not len(addrlist):
            load_addr_seeds()

        ds = []
        for (ip, port) in addrlist:
            d = get_endpoint(ip, port, 8)
            d.addCallback(gotResults)
            d.addErrback(gotFail, ad=ip, po=port)
            ds.append(d)

        d = defer.DeferredList(ds)
        d.addCallback(allDone)
        return d
    else:
        reactor.stop()


def run():
    global plist
    with open("config/peers.pkl", 'rb') as pf:
        plist = pickle.load(pf)
        print "plist loaded: ", plist
    load_addr_seeds()
    d = runClients()
    reactor.run()
    print "Exiting cleanly"
    with gzip.open("backup/savedaddrs.gz",'wb') as f:
        pickle.dump(addrlist, f)


