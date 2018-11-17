# -*- coding: utf-8 -*-

from sanic import Sanic
from sanic.response import json, html
from sanic.exceptions import NotFound

import asyncio
from time import time
from json import loads

### Config ###

app = Sanic("Pool")
app.static('/', './www')

with open('./www/404.html', 'r') as fh:
    notfound = fh.read()


### APP ### 


## Variables ##

previousBlockHash = 0
transactions = []
height = 0
difficulty = "00000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
coinbasetxn = "02000000011da9283b4ddf8d89eb996988b89ead56cecdc44041ab38bf787f1206cd90b51e0000000000ffffffff01405dc6000000000017a914dce7a4e41cdb15c9f88ed98d5474e944ca896a038700000000"


## Helper functions ##

def log_access(request):
    """ log all requests to server """
    print("IP: ", request.ip)
    print("path: ", request.path)
    print("query_string: ", request.query_string)
    print("headers: ", request.headers)
    print("args: ", request.args)

    # TODO log info to disk?


## Miner ##

def convert_endianess(txn):
    return txn.decode('hex')[::-1].encode('hex')


def process_share(params):
    print("share received: {} ".format(share))

    with open("share.txt", 'w') as fh:
        fh.write(share)
        return {'error': 'bad share'}

    return {'error': None}


def get_work():
    """ assemble job for miner """

    template = {
       "coinbasetxn": {
       "data": coinbasetxn
        },
        "previousblockhash": previousBlockHash,
        "transactions": transactions,
        "expires": 120,
        "target": difficulty,
        "longpollid": "",
        "height": height,
        "version": 2,
        "curtime": int(time()),
        "mutable": ["coinbase/append"],
        "bits": "ffff001d" # TODO set dynamically
    }

    response = {
        "error": None,
        "result": template,
        "id": 0
    }

    return response
    

@app.route("/mine/<coinaddr>", methods=['GET', 'POST'])
async def respond(request):
    """ handle requests from miners """

    try:
        # parse json
        req_json = loads((request.body).decode("utf-8"))
        method = req_json['method']

        if method == 'submitblock':
            share = loads((request.body).decode("utf-8"))['params'][0]
            response = process_share(share)

        if method == 'getblocktemplate':
            response = get_work()
    
        return json(response)

    except Exception as e:
        print("bad request: {}".format(e))
        return json("bad request", status=400)


## Crawler ##

@app.route("/push/<crawler>", methods=['GET', 'POST'])
async def receive(request):
    """ receive information from crawlers """

    # set values

    #global transactions = []
    
    global previousBlockHash = 0
    global height = 0
    global difficulty = 0



### App Config ###

@app.exception(NotFound) # fail silently
def not_found(request, exception):
    return html(notfound, status=404)

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

