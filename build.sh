#!/bin/bash

eval `opam config env`
corebuild -verbose 3 -pkg core,async,cohttp.async $1.byte
