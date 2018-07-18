from sanic import Sanic
from sanic.response import json
from sanic.exceptions import NotFound
from sanic import response

app = Sanic("Pool")
app.static('/', './www')

with open('./www/404.html', 'r') as fh:
    notfound = fh.read()

### APP ### 


def log_access(request):
    print("IP: ", request.ip)
    print("args: ", request.args)
    print("path: ", request.path)
    print("query_string: ", request.query_string)
    print("headers: ", request.headers)

    # TODO log info

@app.route('/fetch', methods=['GET'])
async def provide_task(request):

    log_access(request)

    resp = {"base": "hi", "range": "1-5"}    

    return response.json(resp)
    


@app.exception(NotFound) #fail silently
def not_found(request, exception):
    return response.html(notfound, status=404)


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
