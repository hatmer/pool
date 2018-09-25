# -*- coding: utf-8 -*-

from sanic import Sanic
from sanic.response import json, html
from sanic.exceptions import NotFound

# helper fxns eventually
#from random import randint
from pool.helpers import Task_selector
#from pool.globals import *

import asyncio
from time import time

### Config ###

app = Sanic("Pool")
app.static('/', './www')

with open('./www/404.html', 'r') as fh:
    notfound = fh.read()


### APP ### 

task_selector = Task_selector(1) #TODO put me after next data batch aquisition and make sure is never set to 0
#recently_seen = set()
cached_response = None
lastID = None

def log_access(request):
    """ log all requests to server """
    print("IP: ", request.ip)
    print("path: ", request.path)
    print("query_string: ", request.query_string)
    print("headers: ", request.headers)

    # TODO log info to disk?


# Miner

@app.route('/fetch', methods=['GET'])
async def provide_task(request):
    """ serve tasks to workers when they connect """

    log_access(request)
    
    # verify user agent
    worker_id = request.headers['user-agent']
    
    if not worker_id.startswith('worker'):
        return json({}, status=400) # exit because bad user agent

    # construct block header
    
    version = 2 # block version number
    hashPrevBlock = "" # 256 bits
    hashMerkleRoot = "" # 256 bits
    time = int(time())
    #bits = # target in compact format
    nonce = 0
    
    
    coinbasetxn = ""
    previousblockhash = ""
    transactions = []
    target = ""
    height = 0
    #version = 2
    bits = ""

    template = {
   "coinbasetxn": {
     "data": "0100000001000000000000000000000000000000000000000000000000000000
0000000000ffffffff1302955d0f00456c6967697573005047dc66085fffffffff02fff1052a01
0000001976a9144ebeb1cd26d6227635828d60d3e0ed7d0da248fb88ac01000000000000001976
a9147c866aee1fa2f3b3d5effad576df3dbf1f07475588ac00000000"
   },
   "previousblockhash": "000000004d424dec1c660a68456b8271d09628a80cc62583e5904f5894a2483c",
   "transactions": transactions,
   "expires": 120,
   "target": "00000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
   "longpollid": "",
   "height": height,
   "version": 2,
   "curtime": 1346886758,
   "mutable": [],
   "bits": "ffff001d"
 } 
    
    # construct response 
    unique_identifier = worker_id + request.ip

    # one participant can take at most 1/2 of intervals
    #if unique_identifier == lastID:
    #    lastID = unique_identifier
    #    return json(cached_response)


    s = task_selector.next(unique_identifier)
    resp = {"base": "hi", "seed": s}

    return json(resp)


@app.route('/submit', methods=['GET'])
async def receive_results(request):

    # verify user agent
    worker_id = request.headers['user-agent']
    
    if not worker_id.startswith('worker'):
        return json({}, status=400) # exit because bad user agent


    # extract POW
    try:
        merkleroot = request.args['val']      
        # do something with POW if present
        if merkleroot != "":
            pass # TODO implement

    except Exception as e:
        return json({}, status=400) # exit because bad query string


    return json(resp)


# Front-end

@app.route('/', methods=['GET'])
async def serve_html(request):
    return html("hello")


# Crawler

@app.route('/newBlock', methods=['GET'])
async def receive_data(request):
    return json({})

#@app.route('/newTxns'

#@app.route('/newHeight'



@app.exception(NotFound) #fail silently
def not_found(request, exception):
    return html(notfound, status=404)



### App Config ###

# set the secret key
import os
app.secret_key = os.urandom(24)

# create ssl context
import ssl
context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain('creds/server.crt', keyfile='creds/server.key')


if __name__ == "__main__":
    #app.run(host="0.0.0.0", port=8000)
    app.run(port=8000, debug=True, ssl=context)
