# -*- coding: utf-8 -*-

from pool.globals import *


from random import randint

class Task_selector: # TODO run simulations of this algorithm, add to paper
    def __init__(self, num_clients_last_round):
        self.num = randint(MIN_NONCE, MAX_NONCE)
        self.num_clients_last_round = num_clients_last_round
        self.step = MAX_NONCE / num_clients_last_round
        self.workers_served = 0

    def next(self, ID):

        self.workers_served += 1
        if self.workers_served > self.num_clients_last_round: # served all intervals
            self.num -= self.step / 2 # stagger the intervals
            self.workers_served = 1 # reset count
            self.step *= -1 # go back in the opposite direction

        self.num += self.step

        return self.num % MAX_NONCE


from protocol import Connection_manager
import asyncio

class Client:
    """ Module for high-level interaction with Bitcoin network 
          - logging
          - exception handling
          - interaction logic
    """

    def __init__(self):
        self.cm = Connection_manager()
        self.peers = []

    """async def test(self):
        peer = ("127.0.0.1", 8000)
        s = await self.cm.open(peer)
        res = await cm.handshake(s,peer)
        cm.close(s)
        return res
      """  




