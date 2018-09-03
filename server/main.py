# -*- coding: utf-8 -*-

from sanic import Sanic
from sanic.response import json, html
from sanic.exceptions import NotFound

# helper fxns eventually
#from random import randint
from pool.helpers import Task_selector, Client
#from pool.globals import *

import asyncio

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

client = Client()

def log_access(request):
    """ log all requests to server """
    print("IP: ", request.ip)
    print("path: ", request.path)
    print("query_string: ", request.query_string)
    print("headers: ", request.headers)

    # TODO log info to disk?



def get_hashable_data():
    """ acquire data from network """
    

@app.route('/fetch', methods=['GET'])
async def provide_task(request):
    """ serve tasks to workers when they connect """

    log_access(request)
    
    # verify user agent
    worker_id = request.headers['user-agent']
    
    if not worker_id.startswith('worker'):
        return json({}, status=400) # exit because bad user agent

    # extract POW
    try:
        value = request.args['val']
        # do something with POW if present
        if value != "":
            pass # TODO implement

    except Exception as e:
        return json({}, status=400) # exit because bad query string


    # construct response 
    unique_identifier = worker_id + request.ip

    # one participant can take at most 1/2 of intervals
    #if unique_identifier == lastID:
    #    lastID = unique_identifier
    #    return json(cached_response)
        

    s = task_selector.next(unique_identifier)
    resp = {"base": "hi", "seed": s}    

    return json(resp)
    
@app.exception(NotFound) #fail silently
def not_found(request, exception):
    return html(notfound, status=404)

from protocol import Connection_manager
@app.route('/testCxn', methods=['GET'])
async def test_cxn(request):
    peer = ("127.0.0.1", 18333)
    cm = Connection_manager()
    s = await cm.open(peer)
    res = await cm.handshake(s,peer)
    cm.close(s)
    return html(res)



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
