# -*- coding: utf-8 -*-

from sanic import Sanic
from sanic.response import html, text
from sanic.exceptions import NotFound

import asyncio
from datetime import date

import requests
from requests.auth import HTTPDigestAuth
import json


### Config ###

app = Sanic("Pool")
app.static('/', './www')

with open('./www/404.html', 'r') as fh:
    notfound = fh.read()

url = 'http://188.166.36.137:18081/json_rpc'
headers = {'content-type': 'application/json'}
auth = ('hatmer', 'batteriet55')


### Helper functions ###

def log_access(request):
    """ log all requests to server """
    print("IP: ", request.ip)
    print("path: ", request.path)
    print("query_string: ", request.query_string)
    print("headers: ", request.headers)
    print("args: ", request.args)

    # TODO log info to disk?


### Miner ###

async def get_work():
    """ fetch job for miner via RPC request to node """

    payload = {
      "jsonrpc": "2.0",
      "id": "0",
      "method": "get_block_template",
      "params": {
          "wallet_address": "44GBHzv6ZyQdJkjqZje6KLZ3xSyN1hBSFAnLP6EAqJtCRVzMzZmeXTC2AHKDS9aEDTRKmo6a6o9r9j86pYfhCWDkKjbtcns",
          "reserve_size": 60
          }
      }

    try:      
        response = requests.post(url, auth=HTTPDigestAuth('hatmer', 'batteriet55'), data=json.dumps(payload), headers=headers)
        print("response from node OK: ", response)
        print(response.text)
    except:
        print("could not fetch blocktemplate from node")
        response = "500 - internal error"

    # extract blockhashing blob and difficulty
#    jresp = response.json()

    #result = jresp['result']
    #blob = result['blockhashing_blob']
    #difficulty = result['difficulty']
    # TODO get number of zeros from difficulty

    #return blob + "," + difficulty
    

@app.route("/fetch", methods=['GET'])
async def send_work(request):
    """ handle requests from miners """
    # log access
    log_access(request)

    # log Timestamp:IP:coinaddr
    
    # TODO return blob, difficulty
    response = await get_work()
    return text(response)


@app.route("/submit", methods=['POST'])
async def process_share(request, addr):
    """ handle share submits from miners """
    log_access(request)
    try:
        share = request.args['share']
        payout_address = request.args['addr']
        print("processing share: {}".format(share))
    except Exception as e:
        print("share not received")

    # TODO 2.0 validate input (is from recently seen IP, is json, is correct)


    # send share to node
    retry_count = 10
    while retry_count > 0:
        response = await requests.post(url, data=share, headers=headers)
        if response == good:
            print("share was posted successfully")
            break

        retry_count -= 1

    # record share event
    with open("shares.txt", 'a') as fh:
        msg = str(date()) + "," + payout_address + "," + share
        fh.append(msg)

    return text("ok")


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

