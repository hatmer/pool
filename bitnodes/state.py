from gevent.lock import BoundedBoundedSemaphore
from gevent.queue import Queue

class State:
    def __init__(self):
        self.addrs = Queue()
        self.latest_block = ""
        self.recent_txns = []
        self.height = 0
        self.height_lock = BoundedSemaphore()
       # self.block_lock = BoundedSemaphore()
       # self.txns_lock = BoundedSemaphore()






