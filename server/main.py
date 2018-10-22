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
from json import loads

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
    print("args: ", request.args)

    # TODO log info to disk?


# Miner

def convert_endianess(txn):
    return txn.decode('hex')[::-1].encode('hex')

@app.route('/fetch', methods=['GET'])
async def provide_task(request):
    """ serve tasks to workers when they connect """

    log_access(request)
    
    # verify user agent
    #worker_id = request.headers['user-agent']
    
    #if not worker_id.startswith('worker'):
    #    return json({}, status=400) # exit because bad user agent

    # construct block header
    
    #version = 2 # block version number
    #hashPrevBlock = "" # 256 bits
    #hashMerkleRoot = "" # 256 bits
    #current_time = int(time())
    #bits = # target in compact format
    #nonce = 0
    

    coinbasetxn = "02000000011da9283b4ddf8d89eb996988b89ead56cecdc44041ab38bf787f1206cd90b51e0000000000ffffffff01405dc6000000000017a914dce7a4e41cdb15c9f88ed98d5474e944ca896a038700000000"

    # TODO update cbt amt

    previousBlockHash = ""
    transactions = []
    target = ""
    height = 0
    #version = 2
    bits = ""

    template = {
     "coinbasetxn": {
       "data": coinbasetxn
     },
     "previousblockhash": previousBlockHash,
     "transactions": transactions,
     "expires": 120,
     "target": "00000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
     "longpollid": "",
     "height": height,
     "version": 2,
     "curtime": int(time()),
     "mutable": ["coinbase/append"],
     "bits": "ffff001d"
    } 
    
    response = {
             "error": None,
             "result": template,
             "id": 0
             }

    print(template)

    
    # construct response 
    #unique_identifier = worker_id + request.ip


    return json(response)


@app.route('/submit', methods=['POST'])
async def receive_results(request):

    # verify user agent
    #worker_id = request.headers['user-agent']
    
    #if not worker_id.startswith('worker'):
    #    return json({}, status=400) # exit because bad user agent


    # extract POW
    #try:
    #    merkleroot = request.args['val']      
    #    # do something with POW if present
   #     if merkleroot != "":
   #         pass # TODO implement

    #except Exception as e:
    #    return json({}, status=400) # exit because bad query string

    response = {'error': None}
    
    try:
        share = loads((request.body).decode("utf-8"))['params'][0]
        print("share received: {} ".format(share))
    except Exception as e:
        print("bad share received")
        response = {'error': "invalid share format"}

    with open("share.txt", 'w') as fh:
        fh.write(share)

    return json(response)


# Front-end

@app.route('/', methods=['GET'])
async def serve_html(request):
    return html("hello")


# Crawler

transactions = [] # collect a few and verify that they are new
last_block_hash = 0

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
