# -*- coding: utf-8 -*-

from sanic import Sanic
from sanic.response import json, html, raw
from sanic.exceptions import NotFound

import asyncio
from time import time

import requests
import json

### Config ###

app = Sanic("Pool")
app.static('/', './www')

with open('./www/404.html', 'r') as fh:
    notfound = fh.read()


### APP ### 


## Variables ##

url = 'http://51.254.38.216:18081/json_rpc'
headers = {'content-type': 'application/json'}

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


async def get_work():
    """ fetch job for miner via RPC request to node """

    payload = {
      "jsonrpc": "2.0",
      "id": "0",
      "method": "get_block_template",
      "params": {
          "wallet_address": "",
          "reserve_size": 60
          }
      }
        
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response
    

@app.route("/mine/<coinaddr>", methods=['GET'])
async def send_work(request):
    """ handle requests from miners """

    # log access
    # log Timestamp:IP:coinaddr
    response = await get_work()
    return json(response)


@app.route("/submit/<coinaddr>", methods=['POST'])
async def process_share(request):
    """ handle share submits from miners """
    # TODO log access
    try:
        share = request.args
        print("processing share: {}".format(share))
    except Exception as e:
        print("share not received")

    # TODO validate input (is from recently seen IP, is json, is correct)


    # send share directly to node
    retry_count = 10
    while retry_count > 0:
        response = await requests.post(url, data=share, headers=headers)
        if response == good:
            print("share was posted successfully")
            break

        retry_count -= 1

    # TODO notify me of share

    return raw("ok")


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

