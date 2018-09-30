#!/bin/bash

bitcoind -testnet -printtoconsole -logips -logtimestamps -debug=1 -listen -whitelist=127.0.0.1
#-proxy=127.0.0.1:50

#bitcoind -regtest -printtoconsole
